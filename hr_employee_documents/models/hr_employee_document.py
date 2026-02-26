# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date


class HrEmployeeDocument(models.Model):
    _name = 'hr.employee.document'
    _description = 'HR Employee Document'
    _inherit = 'mail.thread'
    _order = 'upload_date desc, name'
    _rec_name = 'name'

    name = fields.Char(
        string='Document Name',
        required=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        readonly=True,
        store=True,
    )
    document_type_id = fields.Many2one(
        'hr.employee.document.type',
        string='Document Type',
        tracking=True,
    )
    description = fields.Text(
        string='Description',
    )
    file = fields.Binary(
        string='File',
        required=True,
        attachment=True,
    )
    file_name = fields.Char(
        string='File Name',
    )
    upload_date = fields.Date(
        string='Upload Date',
        default=fields.Date.today,
        tracking=True,
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        tracking=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # Computed expiry status fields for visual highlighting
    expiry_status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('no_expiry', 'No Expiry'),
    ], string='Expiry Status', compute='_compute_expiry_status', store=True)

    days_to_expiry = fields.Integer(
        string='Days to Expiry',
        compute='_compute_expiry_status',
        store=True,
    )

    is_own_document = fields.Boolean(
        string='Is Own Document',
        compute='_compute_is_own_document',
    )

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains('upload_date', 'expiry_date')
    def _check_expiry_date(self):
        for rec in self:
            if rec.expiry_date and rec.upload_date and rec.expiry_date < rec.upload_date:
                raise ValidationError(_('Expiry Date cannot be before the Upload Date.'))

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------
    @api.depends('expiry_date')
    def _compute_expiry_status(self):
        today = date.today()
        for rec in self:
            if not rec.expiry_date:
                rec.expiry_status = 'no_expiry'
                rec.days_to_expiry = 0
            else:
                delta = (rec.expiry_date - today).days
                rec.days_to_expiry = delta
                if delta < 0:
                    rec.expiry_status = 'expired'
                elif delta <= 30:
                    rec.expiry_status = 'expiring_soon'
                else:
                    rec.expiry_status = 'valid'

    @api.depends('employee_id')
    def _compute_is_own_document(self):
        for rec in self:
            rec.is_own_document = rec.employee_id.user_id.id == self.env.uid

    # -------------------------------------------------------------------------
    # Access control
    # -------------------------------------------------------------------------
    def _is_hr_manager(self):
        return self.env.user.has_group('hr_employee_documents.group_hr_document_manager')

    def _is_hr_officer(self):
        return self.env.user.has_group('hr_employee_documents.group_hr_document_officer')

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if not self._is_hr_manager() and not self._is_hr_officer():
            domain = list(domain) + [('employee_id.user_id', '=', self.env.uid)]
        return super()._search(domain, offset=offset, limit=limit, order=order)

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and not self.name:
            self.name = f'{self.employee_id.name} - Document'
