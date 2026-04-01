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

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Reference', copy=False, readonly=True,
        index=True, default=lambda self: _('New')
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        default=lambda self: self.env.user.employee_id.id,
        required=True
    )

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        related='employee_id.department_id',
        readonly=True
    )

    first_contract_date = fields.Date(
        string='First Contract Date',
        related='employee_id.first_contract_date',
        store=False,
        readonly=True,
        help='Earliest contract start date (hiring date) for this employee.'
    )

    contract_start_date = fields.Date(
        string="Contract Start Date",
        default=lambda self: self._default_contract_start_date()
    )

    expected_revealing_date = fields.Date(
        string="Last Day of Employee",
        required=True
    )

    approved_revealing_date = fields.Date(
        string="Approved Last Day",
        tracking=True
    )

    resign_confirm_date = fields.Date(
        string="Confirmed Date",
        tracking=True
    )

    reason = fields.Text(
        string="Reason",
        required=True
    )

    resignation_type = fields.Selection(
        RESIGNATION_TYPE,
        string="Type"
    )

    employee_contract = fields.Char(
        string="Contract",
        readonly=True
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('approved', 'Approved'),
            ('cancel', 'Rejected')
        ],
        string='Status',
        default='draft',
        tracking=True
    )

    is_own_record = fields.Boolean(
        compute="_compute_is_own_record"
    )

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------
    @api.depends('employee_id')
    def _compute_is_own_record(self):
        for rec in self:
            rec.is_own_record = rec.employee_id.user_id.id == self.env.uid

    # -------------------------------------------------------------------------
    # Access Control
    # -------------------------------------------------------------------------
    def _is_manager(self):
        return self.env.user.has_group('hr.group_hr_manager')

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if not self._is_manager():
            domain = list(domain) + [
                ('employee_id.user_id', '=', self.env.uid)
            ]
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
                raise ValidationError(_(
                    'A resignation request already exists for %s.'
                ) % rec.employee_id.name)

    # -------------------------------------------------------------------------
    # Defaults & Onchange
    # -------------------------------------------------------------------------
    @api.model
    def _default_contract_start_date(self):
        employee = self.env.user.employee_id
        if not employee:
            return False
        contract = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'open'),
        ], limit=1)
        if contract and contract.date_start:
            return contract.date_start
        # fallback to first_contract_date if no open contract
        return employee.first_contract_date or False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if not self.employee_id:
            return
        contract = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'open'),
        ], limit=1)
        if contract and contract.date_start:
            self.contract_start_date = contract.date_start
            self.employee_contract = contract.name
        else:
            self.contract_start_date = self.employee_id.first_contract_date

    # -------------------------------------------------------------------------
    # Create Override
    # -------------------------------------------------------------------------
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'hr.resignation'
            ) or _('New')

        if not self._is_manager():
            vals['employee_id'] = self.env.user.employee_id.id

        employee_id = vals.get('employee_id')
        if employee_id and not vals.get('contract_start_date'):
            contract = self.env['hr.contract'].sudo().search([
                ('employee_id', '=', employee_id),
                ('state', '=', 'open'),
            ], limit=1)
            if contract and contract.date_start:
                vals['contract_start_date'] = contract.date_start
                vals['employee_contract'] = contract.name
            else:
                # fallback to first_contract_date if no open contract
                emp = self.env['hr.employee'].browse(employee_id)
                vals['contract_start_date'] = emp.first_contract_date

        return super().create(vals)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_confirm_resignation(self):
        for rec in self:
            if not rec.contract_start_date:
                raise ValidationError(_('Please set a Contract Start Date first.'))

            if rec.contract_start_date >= rec.expected_revealing_date:
                raise ValidationError(_('Last day must be after contract start date.'))

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

            # Close active contract
            contract = self.env['hr.contract'].sudo().search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'open'),
            ], limit=1)

            if contract:
                contract.sudo().write({'state': 'close'})  # FIXED from 'cancel' to 'close'
                rec.employee_contract = contract.name

            # Update employee status
            rec.employee_id.sudo().write({
                'resign_date': rec.expected_revealing_date,
                'resigned': rec.resignation_type == 'resigned',
                'fired': rec.resignation_type == 'fired',
                'active': False,
            })

            rec.state = 'approved'
            rec.approved_revealing_date = rec.expected_revealing_date