# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class HrEmployeeDocumentType(models.Model):
    _name = 'hr.employee.document.type'
    _description = 'HR Employee Document Type'
    _order = 'name'

    name = fields.Char(
        string='Document Type',
        required=True,
    )
    code = fields.Char(
        string='Code',
        help='Short unique code for this document type (e.g. ID, PASS, MED)',
    )
    description = fields.Text(
        string='Description',
        help='Additional details about this document type',
    )
    document_count = fields.Integer(
        string='Documents',
        compute='_compute_document_count',
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Document type code must be unique.'),
    ]

    @api.depends('name')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['hr.employee.document'].search_count([
                ('document_type_id', '=', rec.id)
            ])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} Documents',
            'res_model': 'hr.employee.document',
            'view_mode': 'list,form',
            'domain': [('document_type_id', '=', self.id)],
        }
