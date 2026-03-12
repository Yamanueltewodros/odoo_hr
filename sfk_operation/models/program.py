# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions

EDITABLE_IN_RUNNING = {'state', 'message_ids', 'message_follower_ids', 'activity_ids'}


class SfkProgram(models.Model):
    _name = 'sfk.program'
    _description = 'Coaching Program'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    name = fields.Char(string='Program Name', required=True, tracking=True)
    program_type = fields.Selection(
        [('center', 'Center-Based'), ('school', 'School-Based')],
        string='Program Type', default='center', required=True, tracking=True
    )
    course_ids = fields.Many2many(
        'sfk.course', string='Available Courses', required=True
    )
    company_id = fields.Many2one(
        'res.company', string='Branch',
        default=lambda self: self.env.company, tracking=True
    )
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    manager_id = fields.Many2one('res.users', string='Manager', tracking=True)
    supervisor_id = fields.Many2one('res.users', string='Supervisor', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    # Center-based fields
    max_student_capacity = fields.Integer(string='Max Student Capacity')
    default_room_id = fields.Many2one('sfk.room', string='Default Room')
    age_group = fields.Char(string='Age Group')

    # School-based fields
    school_name = fields.Char(string='School Name')
    school_location = fields.Char(string='School Location')
    grade_based = fields.Boolean(string='Grade-Based', default=True)

    # Related records
    term_ids = fields.One2many('sfk.term', 'program_id', string='Terms')
    permanent_schedule_ids = fields.One2many(
        'sfk.permanent.schedule', 'program_id', string='Permanent Schedules'
    )
    student_ids = fields.One2many('sfk.student', 'program_id', string='Students')
    enrollment_ids = fields.One2many('sfk.enrollment', 'program_id', string='Enrollments')
    session_ids = fields.One2many('sfk.session', 'program_id', string='Sessions')

    # Computed counts
    student_count = fields.Integer(compute='_compute_counts', string='Students')
    session_count = fields.Integer(compute='_compute_counts', string='Sessions')
    schedule_count = fields.Integer(compute='_compute_counts', string='Schedules')

    def _compute_counts(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)
            rec.session_count = len(rec.session_ids)
            rec.schedule_count = len(rec.permanent_schedule_ids)

    @api.constrains('start_date', 'end_date')
    def _check_program_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date >= rec.end_date:
                raise exceptions.ValidationError("Program end date must be after start date.")

    def write(self, vals):
        # Only block changes to business fields when not in draft.
        # Always allow state transitions, mail/chatter, and computed field updates.
        if self.env.su:
            return super().write(vals)
        protected_fields = {
            'name', 'program_type', 'course_ids', 'company_id',
            'start_date', 'end_date', 'manager_id', 'supervisor_id',
            'max_student_capacity', 'default_room_id', 'age_group',
            'school_name', 'school_location', 'grade_based',
        }
        changed = set(vals.keys()) & protected_fields
        if changed and any(rec.state != 'draft' for rec in self):
            raise exceptions.UserError(
                "Core program fields can only be edited in Draft state. "
                "Reset to Draft first if a change is needed."
            )
        return super().write(vals)

    def action_run(self):
        for program in self:
            if not program.permanent_schedule_ids:
                raise exceptions.UserError(
                    "Cannot start a program with no permanent schedules defined."
                )
            if not program.term_ids:
                raise exceptions.UserError(
                    "Cannot start a program with no terms defined."
                )
            # Generate sessions per schedule, within each schedule's term window
            for schedule in program.permanent_schedule_ids:
                schedule.generate_sessions(
                    schedule.term_id.start_date,
                    schedule.term_id.end_date
                )
            program.message_post(body="Program started. Sessions generated from schedules.")
        self.write({'state': 'running'})

    def action_close(self):
        for program in self:
            future_sessions = self.env['sfk.session'].search([
                ('program_id', '=', program.id),
                ('start_datetime', '>', fields.Datetime.now()),
                ('state', '!=', 'cancelled'),
            ])
            if future_sessions:
                future_sessions.write({'state': 'cancelled'})
            program.message_post(
                body=f"Program closed. {len(future_sessions)} future sessions cancelled."
            )
        self.write({'state': 'closed'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})


class SfkEnrollment(models.Model):
    _name = 'sfk.enrollment'
    _description = 'Student Enrollment'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    student_id = fields.Many2one(
        'sfk.student', string='Student',
        required=True, ondelete='cascade'
    )
    program_id = fields.Many2one(
        'sfk.program', string='Program',
        required=True, ondelete='cascade'
    )
    center_id = fields.Many2one(
        'res.company', string='Branch',
        required=True, default=lambda self: self.env.company
    )
    term_id = fields.Many2one(
        'sfk.term', string='Term',
        required=True,
        domain="[('program_id', '=', program_id)]"
    )
    course_id = fields.Many2one('sfk.course', string='Course', required=True)
    enrollment_date = fields.Date(
        string='Enrollment Date', default=fields.Date.context_today
    )
    status = fields.Selection([
        ('active', 'Active'),
        ('withdrawn', 'Withdrawn'),
        ('completed', 'Completed'),
    ], string='Status', default='active')

    @api.depends('student_id', 'program_id', 'term_id')
    def _compute_display_name(self):
        for rec in self:
            parts = [
                rec.student_id.name or '',
                rec.program_id.name or '',
                rec.term_id.name or '',
            ]
            rec.display_name = ' / '.join(filter(None, parts))

    @api.onchange('student_id')
    def _onchange_student_id(self):
        if self.student_id and self.student_id.program_id:
            self.program_id = self.student_id.program_id
            self.center_id = self.student_id.program_id.company_id

    _sql_constraints = [
        (
            'student_term_course_unique',
            'unique(student_id, term_id, course_id)',
            'This student is already enrolled in this course for this term.'
        )
    ]

    @api.constrains('program_id', 'student_id')
    def _check_capacity(self):
        for rec in self:
            prog = rec.program_id
            if prog.program_type == 'center' and prog.max_student_capacity > 0:
                # Count EXISTING active enrollments excluding this record
                count = self.search_count([
                    ('program_id', '=', prog.id),
                    ('status', '=', 'active'),
                    ('id', '!=', rec.id),
                ])
                if count >= prog.max_student_capacity:
                    raise exceptions.ValidationError(
                        f"Program '{prog.name}' is at full capacity "
                        f"(max: {prog.max_student_capacity} students)."
                    )
