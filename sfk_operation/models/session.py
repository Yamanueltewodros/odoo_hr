# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


# Fields that may never be modified once a session is Done
_DONE_LOCKED_FIELDS = frozenset({
    'program_id', 'term_id', 'course_id', 'grade',
    'start_datetime', 'end_datetime', 'room_id',
    'lead_instructor_id', 'assistant_instructor_id',
    'center_id', 'manager_id', 'supervisor_id',
})


class SfkSession(models.Model):
    _name = 'sfk.session'
    _description = 'Coaching Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'
    _rec_name = 'name'

    name = fields.Char(string='Session Name', required=True, tracking=True)
    program_id = fields.Many2one(
        'sfk.program', string='Program',
        required=True, ondelete='cascade', tracking=True
    )
    program_type = fields.Selection(
        related='program_id.program_type', store=True
    )
    center_id = fields.Many2one(
        'res.company', string='Branch', required=True
    )
    term_id = fields.Many2one('sfk.term', string='Term', required=True, tracking=True)
    course_id = fields.Many2one('sfk.course', string='Course', required=True)
    grade = fields.Char(string='Grade')

    start_datetime = fields.Datetime(
        string='Start', required=True, tracking=True
    )
    end_datetime = fields.Datetime(
        string='End', required=True, tracking=True
    )
    duration_hours = fields.Float(
        string='Duration (hrs)', compute='_compute_duration', store=True
    )
    room_id = fields.Many2one('sfk.room', string='Room')

    lead_instructor_id = fields.Many2one(
        'hr.employee', string='Lead Instructor', tracking=True
    )
    assistant_instructor_id = fields.Many2one(
        'hr.employee', string='Assistant Instructor'
    )
    manager_id = fields.Many2one('res.users', string='Manager')
    supervisor_id = fields.Many2one('res.users', string='Supervisor')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Execution tracking
    execution_state = fields.Selection([
        ('conducted', 'Conducted'),
        ('not_conducted', 'Not Conducted'),
        ('rescheduled', 'Rescheduled'),
    ], string='Execution', default='conducted', tracking=True)
    reason_not_conducted = fields.Text(string='Reason (if not conducted / rescheduled)')
    school_student_count = fields.Integer(
        string='Students Present (School)',
        help='For school-based programs: total headcount present.'
    )

    # Instructor attendance
    lead_instructor_status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('substituted', 'Substituted'),
    ], string='Lead Status', default='present', tracking=True)
    lead_substitute_id = fields.Many2one(
        'hr.employee', string='Lead Substitute'
    )
    assistant_instructor_status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('substituted', 'Substituted'),
    ], string='Assistant Status', default='present')
    assistant_substitute_id = fields.Many2one(
        'hr.employee', string='Assistant Substitute'
    )

    attendance_ids = fields.One2many(
        'sfk.attendance', 'session_id', string='Student Attendance'
    )
    attendance_count = fields.Integer(
        compute='_compute_attendance_stats', string='Enrolled'
    )
    present_count = fields.Integer(
        compute='_compute_attendance_stats', string='Present'
    )
    attendance_rate = fields.Float(
        compute='_compute_attendance_stats', string='Attendance %'
    )

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                delta = rec.end_datetime - rec.start_datetime
                rec.duration_hours = delta.total_seconds() / 3600
            else:
                rec.duration_hours = 0.0

    @api.depends('attendance_ids', 'attendance_ids.status')
    def _compute_attendance_stats(self):
        for rec in self:
            total = len(rec.attendance_ids)
            present = len(rec.attendance_ids.filtered(
                lambda a: a.status in ('present', 'late')
            ))
            rec.attendance_count = total
            rec.present_count = present
            rec.attendance_rate = (present / total * 100) if total else 0.0

    @api.constrains('start_datetime', 'end_datetime', 'room_id',
                    'lead_instructor_id', 'assistant_instructor_id')
    def _check_conflicts(self):
        for rec in self:
            if not rec.start_datetime or not rec.end_datetime:
                continue
            if rec.start_datetime >= rec.end_datetime:
                raise exceptions.ValidationError(
                    "Session end time must be after start time."
                )
            if rec.state == 'cancelled':
                continue

            # Room overlap
            if rec.room_id:
                overlap = self.search([
                    ('id', '!=', rec.id),
                    ('room_id', '=', rec.room_id.id),
                    ('start_datetime', '<', rec.end_datetime),
                    ('end_datetime', '>', rec.start_datetime),
                    ('state', '!=', 'cancelled'),
                ], limit=1)
                if overlap:
                    raise exceptions.ValidationError(
                        f"Room '{rec.room_id.name}' is already booked for "
                        f"'{overlap.name}' during this time slot."
                    )

            # Instructor overlaps
            for instr in filter(None, [rec.lead_instructor_id, rec.assistant_instructor_id]):
                conflict = self.search([
                    ('id', '!=', rec.id),
                    '|',
                    ('lead_instructor_id', '=', instr.id),
                    ('assistant_instructor_id', '=', instr.id),
                    ('start_datetime', '<', rec.end_datetime),
                    ('end_datetime', '>', rec.start_datetime),
                    ('state', '!=', 'cancelled'),
                ], limit=1)
                if conflict:
                    raise exceptions.ValidationError(
                        f"Instructor '{instr.name}' is already assigned to "
                        f"'{conflict.name}' during this time slot."
                    )

    def write(self, vals):
        # Prevent edits to core fields on Done sessions (allow mail/chatter always)
        if not self.env.su:
            locked = set(vals.keys()) & _DONE_LOCKED_FIELDS
            if locked and any(rec.state == 'done' for rec in self):
                raise exceptions.UserError(
                    f"Cannot modify {', '.join(locked)} on a completed session."
                )
        return super().write(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.write({'state': 'confirmed'})
            if rec.program_type == 'center':
                rec.action_load_students()
            rec.message_post(body="Session confirmed.")

    def action_done(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise exceptions.UserError(
                    "Only confirmed sessions can be marked as Done."
                )
        self.write({'state': 'done'})
        for rec in self:
            rec.message_post(body="Session marked as done.")

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        for rec in self:
            rec.message_post(body="Session cancelled.")

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_load_students(self):
        """Auto-load enrolled students into attendance for center-based sessions."""
        self.ensure_one()
        if self.program_type != 'center':
            return
        Attendance = self.env['sfk.attendance']
        enrollments = self.env['sfk.enrollment'].search([
            ('program_id', '=', self.program_id.id),
            ('term_id', '=', self.term_id.id),
            ('course_id', '=', self.course_id.id),
            ('status', '=', 'active'),
        ])
        new_count = 0
        for enr in enrollments:
            exists = Attendance.search([
                ('session_id', '=', self.id),
                ('student_id', '=', enr.student_id.id),
            ], limit=1)
            if not exists:
                Attendance.create({
                    'session_id': self.id,
                    'student_id': enr.student_id.id,
                    'status': 'absent',
                })
                new_count += 1
        if new_count:
            self.message_post(body=f"{new_count} student(s) loaded into attendance.")
        return new_count
