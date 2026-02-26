# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

RESIGNATION_TYPE = [
    ('resigned', 'Normal Resignation'),
    ('fired', 'Fired by the company'),
]


class HrResignation(models.Model):
    _name = 'hr.resignation'
    _description = 'HR Resignation'
    _inherit = 'mail.thread'
    _rec_name = 'employee_id'

    name = fields.Char(
        string='Order Reference', copy=False, readonly=True,
        index=True, default=lambda self: _('New')
    )
    employee_id = fields.Many2one(
        'hr.employee', string="Employee",
        default=lambda self: self.env.user.employee_id.id,
        help='Employee submitting this resignation',
    )
    department_id = fields.Many2one(
        'hr.department', string="Department",
        related='employee_id.department_id', readonly=True
    )
    resign_confirm_date = fields.Date(string="Confirmed Date", tracking=True)
    approved_revealing_date = fields.Date(string="Approved Last Day Of Employee", tracking=True)
    contract_start_date = fields.Date(string="Contract Start Date")
    expected_revealing_date = fields.Date(string="Last Day of Employee", required=True)
    reason = fields.Text(string="Reason", required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'),
         ('approved', 'Approved'), ('cancel', 'Rejected')],
        string='Status', default='draft', tracking=True
    )
    resignation_type = fields.Selection(
        selection=RESIGNATION_TYPE,
        help="Normal resignation or fired by the company"
    )
    employee_contract = fields.Char(string="Contract", readonly=True)

    # Computed field to check if the current user owns this record
    is_own_record = fields.Boolean(
        string="Is Own Record",
        compute="_compute_is_own_record"
    )

    @api.depends('employee_id')
    def _compute_is_own_record(self):
        for rec in self:
            rec.is_own_record = rec.employee_id.user_id.id == self.env.uid

    # -------------------------------------------------------------------------
    # Access Control
    # -------------------------------------------------------------------------
    def _is_manager(self):
        return self.env.user.has_group('hr_resignation.group_hr_resignation_manager')

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if not self._is_manager():
            domain = list(domain) + [('employee_id.user_id', '=', self.env.uid)]
        return super()._search(domain, offset=offset, limit=limit, order=order)

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains('employee_id', 'state')
    def _check_no_duplicate_active_request(self):
        for rec in self:
            duplicate = self.env['hr.resignation'].sudo().search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ['confirm', 'approved']),
                ('id', '!=', rec.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    _('A resignation request in Confirmed or Approved state already exists for %s.')
                    % rec.employee_id.name
                )

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if not self.employee_id:
            return
        active_contract = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'open'),
        ], limit=1)
        if active_contract:
            self.contract_start_date = active_contract.date_start
            self.employee_contract = active_contract.name

    # -------------------------------------------------------------------------
    # Overrides
    # -------------------------------------------------------------------------
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.resignation') or _('New')
        if not self._is_manager():
            vals['employee_id'] = self.env.user.employee_id.id
        return super().create(vals)

    # -------------------------------------------------------------------------
    # Button actions
    # -------------------------------------------------------------------------
    def action_confirm_resignation(self):
        for rec in self:
            if not rec.contract_start_date:
                raise ValidationError(_('Please set a Contract Start Date before confirming.'))
            if rec.contract_start_date >= rec.expected_revealing_date:
                raise ValidationError(_('Last Day must be after Contract Start Date.'))
            rec.state = 'confirm'
            rec.resign_confirm_date = fields.Date.today()

    def action_cancel_resignation(self):
        for rec in self:
            rec.state = 'cancel'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_approve_resignation(self):
        for rec in self:
            if not rec.expected_revealing_date:
                raise ValidationError(_('Please enter the expected last day.'))

            active_contract = self.env['hr.contract'].sudo().search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'open'),
            ], limit=1)

            if active_contract:
                active_contract.sudo().state = 'cancel'
                rec.employee_contract = active_contract.name

            rec.state = 'approved'
            rec.approved_revealing_date = rec.expected_revealing_date