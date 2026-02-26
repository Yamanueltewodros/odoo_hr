# -*- coding: utf-8 -*-
from odoo import models, fields, api

RATING = [
    ('1', '1 - Poor'),
    ('2', '2 - Fair'),
    ('3', '3 - Average'),
    ('4', '4 - Good'),
    ('5', '5 - Excellent'),
]


class HrExitInterview(models.Model):
    _name = 'hr.exit.interview'
    _description = 'Employee Exit Interview'
    _inherit = 'mail.thread'
    _order = 'interview_date desc'

    name = fields.Char(
        string="Reference", required=True, copy=False,
        readonly=True, default="New"
    )
    employee_id = fields.Many2one(
        'hr.employee', string="Employee", required=True
    )
    department_id = fields.Many2one(
        'hr.department', string="Department",
        related='employee_id.department_id', readonly=True
    )
    resignation_id = fields.Many2one(
        'hr.resignation', string="Related Resignation",
        domain="[('employee_id','=',employee_id)]"
    )
    interview_date = fields.Date(
        string="Interview Date", required=True,
        default=fields.Date.today
    )
    interviewer_id = fields.Many2one(
        'hr.employee', string="Interviewer",
        default=lambda self: self.env.user.employee_id.id
    )
    exit_reason = fields.Selection([
        ('resignation', 'Resignation'),
        ('termination', 'Termination'),
        ('contract_end', 'End of Contract'),
        ('retirement', 'Retirement'),
        ('other', 'Other'),
    ], string="Reason for Leaving")

    would_rehire = fields.Boolean(string="Would Rehire?")

    work_environment_rating = fields.Selection(
        RATING, string="Work Environment Rating"
    )
    management_rating = fields.Selection(
        RATING, string="Management Rating"
    )
    compensation_rating = fields.Selection(
        RATING, string="Compensation Rating"
    )
    growth_rating = fields.Selection(
        RATING, string="Growth Opportunities Rating"
    )

    feedback = fields.Text(string="General Feedback")
    recommendation = fields.Text(string="Recommendations")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string="Status", default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.exit.interview') or 'New'
        return super().create(vals)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_done(self):
        self.state = 'done'

    def action_reset_draft(self):
        self.state = 'draft'