
# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    first_contract_date = fields.Date(
        string='First Contract Date',
        compute='_compute_first_contract_date',
        store=False,
        readonly=True,
        help='Earliest contract start date (hiring date) for this employee.'
    )

    resign_date = fields.Date(string='Resign Date', readonly=True, help="Date of the resignation")
    resigned = fields.Boolean(string="Resigned", default=False, help="If checked then employee has resigned")
    fired = fields.Boolean(string="Fired", default=False, help="If checked then employee has been fired")

    @api.depends('contract_ids.date_start')
    def _compute_first_contract_date(self):
        for emp in self:
            if emp.contract_ids:
                dates = [c.date_start for c in emp.contract_ids if c.date_start]
                emp.first_contract_date = min(dates) if dates else False
            else:
                emp.first_contract_date = False


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    disciplinary_termination_date = fields.Date(
        related='employee_id.disciplinary_termination_date',
        readonly=True
    )
    disciplinary_termination_case_id = fields.Many2one(
        'hr.disciplinary.case',
        related='employee_id.disciplinary_termination_case_id',
        readonly=True
    )
    employee_status = fields.Selection(
        related='employee_id.employee_status',
        readonly=True
    )
    resign_date = fields.Date(
        related='employee_id.resign_date',
        readonly=True
    )
    resigned = fields.Boolean(
        related='employee_id.resigned',
        readonly=True
    )
    fired = fields.Boolean(
        related='employee_id.fired',
        readonly=True
    )