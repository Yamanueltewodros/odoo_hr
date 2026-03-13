# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import timedelta


class SfkWeeklyReport(models.Model):
    """
    Consolidated weekly report submitted by the Head of Resources & Standards
    to the Head of Operation every week.
    Auto-aggregates compliance checks, open audit findings, equipment incidents,
    and staff training from the past 7 days.
    """
    _name = 'sfk.weekly.report'
    _description = 'Consolidated Weekly Standards Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'week_start desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Report Reference', required=True, readonly=True,
        default='New', copy=False
    )
    week_start = fields.Date(
        string='Week Starting', required=True,
        default=fields.Date.context_today, tracking=True
    )
    week_end = fields.Date(
        string='Week Ending', compute='_compute_week_end', store=True
    )
    company_id = fields.Many2one(
        'res.company', string='Branch',
        default=lambda self: self.env.company
    )
    prepared_by = fields.Many2one(
        'res.users', string='Prepared By',
        default=lambda self: self.env.user, readonly=True
    )

    # ── Auto-aggregated KPIs ─────────────────────────────────────────────
    compliance_checks_total = fields.Integer(
        string='Compliance Checks This Week', compute='_compute_kpis', store=True
    )
    compliance_checks_failed = fields.Integer(
        string='Failed Checks', compute='_compute_kpis', store=True
    )
    compliance_checks_escalated = fields.Integer(
        string='Escalated Checks', compute='_compute_kpis', store=True
    )
    open_audit_findings = fields.Integer(
        string='Open Audit Findings', compute='_compute_kpis', store=True
    )
    critical_audit_findings = fields.Integer(
        string='Critical Findings', compute='_compute_kpis', store=True
    )
    equipment_incidents_new = fields.Integer(
        string='New Equipment Incidents', compute='_compute_kpis', store=True
    )
    equipment_incidents_open = fields.Integer(
        string='Open Incidents (Total)', compute='_compute_kpis', store=True
    )
    trainings_completed = fields.Integer(
        string='Trainings Completed', compute='_compute_kpis', store=True
    )

    # ── Narrative sections ───────────────────────────────────────────────
    logistics_summary = fields.Text(
        string='Logistics & Operations Summary',
        help='Summary of transportation, storage, and resource distribution this week.'
    )
    standards_summary = fields.Text(
        string='Standards & Compliance Summary',
        help='Key compliance observations, curriculum quality issues, child safety notes.'
    )
    achievements = fields.Text(
        string='Achievements / Positive Highlights'
    )
    challenges = fields.Text(
        string='Challenges & Risks'
    )
    action_items = fields.Text(
        string='Action Items for Next Week'
    )
    escalations = fields.Text(
        string='Matters Escalated to Head of Operation'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted to Head of Operation'),
        ('acknowledged', 'Acknowledged'),
    ], default='draft', string='Status', tracking=True)

    submitted_date = fields.Datetime(string='Submitted On', readonly=True)

    # ── Compute ──────────────────────────────────────────────────────────
    @api.depends('week_start')
    def _compute_week_end(self):
        for rec in self:
            if rec.week_start:
                rec.week_end = rec.week_start + timedelta(days=6)
            else:
                rec.week_end = False

    @api.depends('week_start', 'week_end', 'company_id')
    def _compute_kpis(self):
        for rec in self:
            if not rec.week_start or not rec.week_end:
                rec.compliance_checks_total = 0
                rec.compliance_checks_failed = 0
                rec.compliance_checks_escalated = 0
                rec.open_audit_findings = 0
                rec.critical_audit_findings = 0
                rec.equipment_incidents_new = 0
                rec.equipment_incidents_open = 0
                rec.trainings_completed = 0
                continue

            company_domain = [('company_id', '=', rec.company_id.id)] if rec.company_id else []

            # Compliance checks
            checks = self.env['sfk.compliance.check'].search(
                company_domain + [
                    ('check_date', '>=', rec.week_start),
                    ('check_date', '<=', rec.week_end),
                ]
            )
            rec.compliance_checks_total = len(checks)
            rec.compliance_checks_failed = len(checks.filtered(
                lambda c: c.overall_result == 'fail'
            ))
            rec.compliance_checks_escalated = len(checks.filtered(
                lambda c: c.escalate_to_head
            ))

            # Open audit findings
            findings = self.env['sfk.audit.finding'].search([
                ('state', 'not in', ('resolved', 'accepted')),
            ])
            rec.open_audit_findings = len(findings)
            rec.critical_audit_findings = len(findings.filtered(
                lambda f: f.severity == 'critical'
            ))

            # Equipment incidents
            new_incidents = self.env['sfk.equipment.incident'].search(
                company_domain + [
                    ('incident_date', '>=', rec.week_start),
                    ('incident_date', '<=', rec.week_end),
                ]
            )
            rec.equipment_incidents_new = len(new_incidents)
            rec.equipment_incidents_open = self.env['sfk.equipment.incident'].search_count(
                company_domain + [('state', 'in', ('reported', 'investigating'))]
            )

            # Trainings
            rec.trainings_completed = self.env['sfk.staff.training'].search_count(
                company_domain + [
                    ('training_date', '>=', rec.week_start),
                    ('training_date', '<=', rec.week_end),
                    ('state', '=', 'completed'),
                ]
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name == 'New':
                rec.name = self.env['ir.sequence'].next_by_code('sfk.weekly.report') or 'New'
        return records

    def action_submit(self):
        for rec in self:
            if not rec.standards_summary and not rec.logistics_summary:
                raise exceptions.UserError(
                    'Please complete at least the Standards Summary or Logistics Summary before submitting.'
                )
        self.write({
            'state': 'submitted',
            'submitted_date': fields.Datetime.now(),
        })
        for rec in self:
            rec.message_post(body=f"Weekly report '{rec.name}' submitted to Head of Operation.")

    def action_acknowledge(self):
        self.write({'state': 'acknowledged'})
        for rec in self:
            rec.message_post(body="Report acknowledged.")

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_refresh_kpis(self):
        """Manually trigger KPI recomputation."""
        self._compute_kpis()
