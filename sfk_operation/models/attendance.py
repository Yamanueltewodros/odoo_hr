# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SfkAttendance(models.Model):
    _name = 'sfk.attendance'
    _description = 'Student Attendance'
    _order = 'session_id, student_id'

    session_id = fields.Many2one(
        'sfk.session', string='Session',
        required=True, ondelete='cascade'
    )
    student_id = fields.Many2one(
        'sfk.student', string='Student', required=True
    )
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ], string='Status', default='absent', required=True)
    notes = fields.Char(string='Notes')
    checked_by = fields.Many2one(
        'res.users', string='Recorded By', readonly=True
    )
    checked_date = fields.Datetime(string='Recorded On', readonly=True)

    # Convenience related fields for reporting
    program_id = fields.Many2one(
        related='session_id.program_id', store=True, string='Program'
    )
    term_id = fields.Many2one(
        related='session_id.term_id', store=True, string='Term'
    )
    course_id = fields.Many2one(
        related='session_id.course_id', store=True, string='Course'
    )
    session_date = fields.Datetime(
        related='session_id.start_datetime', store=True, string='Session Date'
    )

    _sql_constraints = [
        (
            'session_student_unique',
            'unique(session_id, student_id)',
            'This student already has an attendance record for this session.'
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('checked_by', self.env.uid)
            vals.setdefault('checked_date', fields.Datetime.now())
            self._validate_student_eligibility(
                vals.get('session_id'), vals.get('student_id')
            )
        return super().create(vals_list)

    def write(self, vals):
        if 'student_id' in vals or 'session_id' in vals:
            for rec in self:
                sid = vals.get('session_id', rec.session_id.id)
                stid = vals.get('student_id', rec.student_id.id)
                self._validate_student_eligibility(sid, stid)
        if 'status' in vals:
            for rec in self:
                rec.checked_by = self.env.uid
                rec.checked_date = fields.Datetime.now()
        return super().write(vals)

    def _validate_student_eligibility(self, session_id, student_id):
        if not session_id or not student_id:
            return
        session = self.env['sfk.session'].browse(session_id)
        if session.program_type != 'center':
            return
        enrollment = self.env['sfk.enrollment'].search([
            ('student_id', '=', student_id),
            ('program_id', '=', session.program_id.id),
            ('term_id', '=', session.term_id.id),
            ('course_id', '=', session.course_id.id),
            ('status', '=', 'active'),
        ], limit=1)
        if not enrollment:
            student = self.env['sfk.student'].browse(student_id)
            raise exceptions.ValidationError(
                f"Student '{student.name}' is not actively enrolled in the "
                f"program/term/course for this session."
            )
