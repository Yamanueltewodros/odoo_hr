# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SfkCorrectiveAction(models.Model):
    """
    Formal Corrective Action Plan (CAP) linked to audit findings or compliance failures.
    Closes the loop: finding → CAP → verified resolution.
    """
    _name = 'sfk.corrective.action'
    _description = 'Corrective Action Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date, priority desc'
    _rec_name = 'name'

    name = fields.Char(
        string='CAP Reference', required=True, readonly=True,
        default='New', copy=False
    )
    title = fields.Char(string='Issue Title', required=True, tracking=True)
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'High'),
        ('2', 'Critical'),
    ], string='Priority', default='0', tracking=True)

    # Source
    source = fields.Selection([
        ('audit_finding', 'Audit Finding'),
        ('compliance_check', 'Compliance Check'),
        ('equipment_incident', 'Equipment Incident'),
        ('management_directive', 'Management Directive'),
        ('other', 'Other'),
    ], string='Source', required=True, tracking=True)
    audit_finding_id = fields.Many2one(
        'sfk.audit.finding', string='Audit Finding',
        invisible="source != 'audit_finding'"
    )
    compliance_check_id = fields.Many2one(
        'sfk.compliance.check', string='Compliance Check',
        invisible="source != 'compliance_check'"
    )
    equipment_incident_id = fields.Many2one(
        'sfk.equipment.incident', string='Equipment Incident',
        invisible="source != 'equipment_incident'"
    )

    # Ownership
    root_cause = fields.Text(string='Root Cause Analysis', required=True)
    corrective_action = fields.Text(string='Corrective Action Description', required=True)
    preventive_action = fields.Text(string='Preventive Measures')
    responsible_id = fields.Many2one(
        'hr.employee', string='Responsible Person', required=True, tracking=True
    )
    approved_by = fields.Many2one(
        'res.users', string='Approved By',
        default=lambda self: self.env.user
    )
    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Branch',
        default=lambda self: self.env.company
    )

    # Resolution
    completion_date = fields.Date(string='Completed On', readonly=True)
    verification_notes = fields.Text(string='Verification Notes')
    verified_by = fields.Many2one('res.users', string='Verified By', readonly=True)
    verified_date = fields.Date(string='Verified On', readonly=True)

    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed - Pending Verification'),
        ('verified', 'Verified & Closed'),
        ('overdue', 'Overdue'),
    ], default='open', string='Status', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name == 'New':
                rec.name = self.env['ir.sequence'].next_by_code('sfk.corrective.action') or 'New'
        return records

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        for rec in self:
            if not rec.corrective_action:
                raise exceptions.UserError('Please describe the corrective action taken.')
        self.write({'state': 'completed', 'completion_date': fields.Date.today()})

    def action_verify(self):
        for rec in self:
            if not rec.verification_notes:
                raise exceptions.UserError('Please add verification notes before closing.')
        self.write({
            'state': 'verified',
            'verified_by': self.env.uid,
            'verified_date': fields.Date.today(),
        })

    def action_reopen(self):
        self.write({'state': 'in_progress'})

