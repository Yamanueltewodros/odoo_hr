# -*- coding: utf-8 -*-
from odoo import fields, models

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    resign_date = fields.Date(string='Resign Date', readonly=True, help="Date of the resignation")
    resigned = fields.Boolean(string="Resigned", default=False, help="If checked then employee has resigned")
    fired = fields.Boolean(string="Fired", default=False, help="If checked then employee has been fired")