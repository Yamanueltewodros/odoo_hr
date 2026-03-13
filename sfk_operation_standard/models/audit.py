# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SfkAudit(models.Model):
    """
    Formal audit records matching the Head of R&S duty cycle:
      - weekly   : workshop delivery, facility readiness, resource usage
      - quarterly: materials, facilities, staff practices
      - annual   : full org audit covering staff, materials, facilities, compliance
    """
    _name = 'sfk.audit'
    _description = 'SFK Organizational Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'audit_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Audit Reference', required=True, readonly=True,
        default='New', copy=False
    )
    audit_type = fields.Selection([
        ('weekly', 'Weekly Audit'),
        ('quarterly', 'Quarterly Audit'),
        ('annual', 'Annual Audit'),
        ('special', 'Special / Event Audit'),
    ], string='Audit Type', required=True, tracking=True)
    audit_date = fields.Date(
        string='Audit Date', required=True,
        default=fields.Date.context_today, tracking=True
    )
    company_id = fields.Many2one(
        'res.company', string='Branch',
        default=lambda self: self.env.company
    )
    lead_auditor_id = fields.Many2one(
        'res.users', string='Lead Auditor',
        default=lambda self: self.env.user, tracking=True
    )
    program_ids = fields.Many2many(
        'sfk.program', string='Programs Audited'
    )

    # ── Scope areas ──────────────────────────────────────────────────────
    scope_workshop_delivery = fields.Boolean(string='Workshop Delivery', default=True)
    scope_facility_readiness = fields.Boolean(string='Facility Readiness', default=True)
    scope_resource_usage = fields.Boolean(string='Resource Usage', default=True)
    scope_staff_practices = fields.Boolean(string='Staff Practices')
    scope_materials = fields.Boolean(string='Materials Inventory')
    scope_compliance = fields.Boolean(string='Compliance & Standards')
    scope_child_safety = fields.Boolean(string='Child Safety')

    # ── Findings ─────────────────────────────────────────────────────────
    finding_ids = fields.One2many('sfk.audit.finding', 'audit_id', string='Findings')
    finding_count = fields.Integer(compute='_compute_finding_count', string='Finding Count')
    critical_count = fields.Integer(compute='_compute_finding_count', string='Critical')
    open_count = fields.Integer(compute='_compute_finding_count', string='Open')

    summary = fields.Text(string='Executive Summary')
    recommendations = fields.Text(string='Recommendations')
    follow_up_date = fields.Date(string='Follow-up Due Date')

    # ── State ────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Planning'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
        ('acknowledged', 'Acknowledged by Head of Operation'),
        ('closed', 'Closed'),
    ], default='draft', string='Status', tracking=True)

    submitted_date = fields.Date(string='Submitted On', readonly=True)
    closed_date = fields.Date(string='Closed On', readonly=True)

    # ── Compute ──────────────────────────────────────────────────────────
    @api.depends('finding_ids', 'finding_ids.severity', 'finding_ids.state')
    def _compute_finding_count(self):
        for rec in self:
            rec.finding_count = len(rec.finding_ids)
            rec.critical_count = len(rec.finding_ids.filtered(
                lambda f: f.severity == 'critical'
            ))
            rec.open_count = len(rec.finding_ids.filtered(
                lambda f: f.state not in ('resolved', 'accepted')
            ))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name == 'New':
                code = 'sfk.audit.weekly'
                if rec.audit_type == 'quarterly':
                    code = 'sfk.audit.quarterly'
                elif rec.audit_type == 'annual':
                    code = 'sfk.audit.annual'
                elif rec.audit_type == 'special':
                    code = 'sfk.audit.special'
                rec.name = self.env['ir.sequence'].next_by_code(code) or 'New'
        return records

    # ── State transitions ────────────────────────────────────────────────
    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_submit(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise exceptions.UserError('Audit must be in progress before submitting.')
            if not rec.summary:
                raise exceptions.UserError('Please add an Executive Summary before submitting.')
        self.write({'state': 'submitted', 'submitted_date': fields.Date.today()})
        for rec in self:
            rec.message_post(body=f"Audit '{rec.name}' submitted for acknowledgment.")

    def action_acknowledge(self):
        self.write({'state': 'acknowledged'})
        for rec in self:
            rec.message_post(body="Audit acknowledged by Head of Operation.")

    def action_close(self):
        for rec in self:
            open_critical = rec.finding_ids.filtered(
                lambda f: f.severity == 'critical' and f.state not in ('resolved', 'accepted')
            )
            if open_critical:
                raise exceptions.UserError(
                    f"Cannot close audit: {len(open_critical)} critical finding(s) are still open."
                )
        self.write({'state': 'closed', 'closed_date': fields.Date.today()})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class SfkAuditFinding(models.Model):
    """
    Individual finding raised within an audit.
    """
    _name = 'sfk.audit.finding'
    _description = 'Audit Finding'
    _order = 'severity, name'

    audit_id = fields.Many2one(
        'sfk.audit', required=True, ondelete='cascade', string='Audit'
    )
    name = fields.Char(string='Finding', required=True)
    area = fields.Selection([
        ('workshop', 'Workshop Delivery'),
        ('facility', 'Facility'),
        ('resource', 'Resources / Materials'),
        ('staff', 'Staff Practice'),
        ('compliance', 'Compliance / Standards'),
        ('child_safety', 'Child Safety'),
        ('other', 'Other'),
    ], string='Area', required=True)
    severity = fields.Selection([
        ('observation', 'Observation'),
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
    ], string='Severity', required=True, default='minor')
    description = fields.Text(string='Description')
    recommendation = fields.Text(string='Recommended Action')
    responsible_id = fields.Many2one('hr.employee', string='Responsible Person')
    due_date = fields.Date(string='Due Date')
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('accepted', 'Risk Accepted'),
    ], string='Status', default='open')
    resolution_notes = fields.Text(string='Resolution Notes')

    def action_resolve(self):
        self.write({'state': 'resolved'})

    def action_accept_risk(self):
        self.write({'state': 'accepted'})
