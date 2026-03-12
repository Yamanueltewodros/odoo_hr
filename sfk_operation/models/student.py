# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date


class SfkStudent(models.Model):
    _name = 'sfk.student'
    _description = 'Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(
        string='Age', compute='_compute_age', store=True
    )
    program_id = fields.Many2one(
        'sfk.program', string='Primary Program',
        ondelete='set null', tracking=True
    )
    enrollment_date = fields.Date(
        string='Registration Date', default=fields.Date.context_today
    )
    status = fields.Selection([
        ('active', 'Active'),
        ('withdrawn', 'Withdrawn'),
        ('completed', 'Completed'),
    ], string='Status', default='active', tracking=True)
    enrollment_ids = fields.One2many(
        'sfk.enrollment', 'student_id', string='Enrollments'
    )
    notes = fields.Text(string='Notes')

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                d = rec.date_of_birth
                rec.age = (
                    today.year - d.year
                    - ((today.month, today.day) < (d.month, d.day))
                )
            else:
                rec.age = 0

    def action_set_active(self):
        self.write({'status': 'active'})
        self.message_post(body="Student set to Active.")

    def action_set_withdrawn(self):
        self.write({'status': 'withdrawn'})
        self.message_post(body="Student withdrawn.")

    def action_set_completed(self):
        self.write({'status': 'completed'})
        self.message_post(body="Student marked as Completed.")
