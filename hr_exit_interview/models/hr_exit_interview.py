# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
        'hr.employee', string="Employee",
        required=True, ondelete='cascade', tracking=True
    )
    department_id = fields.Many2one(
        'hr.department', string="Department",
        related='employee_id.department_id', readonly=True
    )
    resignation_id = fields.Many2one(
        'hr.resignation', string="Related Resignation",
        domain="[('employee_id', '=', employee_id)]",
        tracking=True
    )
    interview_date = fields.Date(
        string="Interview Date",
        default=fields.Date.today,
        required=True, tracking=True
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
    ], string="Reason for Leaving", required=True, tracking=True)

    # Ratings
    work_environment_rating = fields.Selection([
        ('1', 'Very Poor'), ('2', 'Poor'), ('3', 'Average'),
        ('4', 'Good'), ('5', 'Excellent'),
    ], string="Work Environment Rating")
    management_rating = fields.Selection([
        ('1', 'Very Poor'), ('2', 'Poor'), ('3', 'Average'),
        ('4', 'Good'), ('5', 'Excellent'),
    ], string="Management Rating")
    compensation_rating = fields.Selection([
        ('1', 'Very Poor'), ('2', 'Poor'), ('3', 'Average'),
        ('4', 'Good'), ('5', 'Excellent'),
    ], string="Compensation Rating")
    growth_rating = fields.Selection([
        ('1', 'Very Poor'), ('2', 'Poor'), ('3', 'Average'),
        ('4', 'Good'), ('5', 'Excellent'),
    ], string="Growth Opportunities Rating")

    feedback = fields.Text(string="Feedback on Work Environment")
    recommendation = fields.Text(string="Recommendations for Improvement")
    would_rehire = fields.Selection([
        ('yes', 'Yes'), ('no', 'No'), ('maybe', 'Maybe'),
    ], string="Would You Rehire This Employee?")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], default='draft', string="Status", tracking=True)

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company
    )

    # -------------------------------------------------------------------------
    # Overrides
    # -------------------------------------------------------------------------
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.exit.interview') or 'New'
        return super().create(vals)

    # -------------------------------------------------------------------------
    # Button actions
    # -------------------------------------------------------------------------
    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})