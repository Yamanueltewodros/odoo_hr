# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SfkComplianceCheck(models.Model):
    """
    Daily / per-session compliance check performed by the Head of Resources & Standards
    or a delegated reviewer.  Each record covers one session (or a manual spot-check)
    and scores compliance against SFK's three key pillars:
      - Child Safety & Ethics
      - Curriculum Quality (SFK Standards)
      - Facility / Resource Readiness
    """
    _name = 'sfk.compliance.check'
    _description = 'Workshop Compliance Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'check_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference', required=True, readonly=True,
        default='New', copy=False
    )
    check_date = fields.Date(
        string='Check Date', required=True,
        default=fields.Date.context_today, tracking=True
    )
    session_id = fields.Many2one(
        'sfk.session', string='Session',
        ondelete='set null', tracking=True
    )
    program_id = fields.Many2one(
        'sfk.program', string='Program',
        compute='_compute_program_id', store=True,
        readonly=False, tracking=True
    )
    company_id = fields.Many2one(
        'res.company', string='Branch',
        default=lambda self: self.env.company
    )
    reviewer_id = fields.Many2one(
        'res.users', string='Reviewed By',
        default=lambda self: self.env.user, readonly=True
    )

    # ── Child Safety & Ethics ───────────────────────────────────────────
    child_safety_score = fields.Selection([
        ('pass', 'Pass'),
        ('minor', 'Minor Issue'),
        ('major', 'Major Issue'),
        ('fail', 'Fail'),
    ], string='Child Safety & Ethics', required=True, default='pass', tracking=True)
    child_safety_notes = fields.Text(string='Child Safety Notes')

    # ── Curriculum / SFK Standards ──────────────────────────────────────
    curriculum_score = fields.Selection([
        ('pass', 'Pass'),
        ('minor', 'Minor Issue'),
        ('major', 'Major Issue'),
        ('fail', 'Fail'),
    ], string='Curriculum Delivery', required=True, default='pass', tracking=True)
    curriculum_notes = fields.Text(string='Curriculum Notes')

    # ── Facility / Resource Readiness ───────────────────────────────────
    facility_score = fields.Selection([
        ('pass', 'Pass'),
        ('minor', 'Minor Issue'),
        ('major', 'Major Issue'),
        ('fail', 'Fail'),
    ], string='Facility & Resources', required=True, default='pass', tracking=True)
    facility_notes = fields.Text(string='Facility Notes')

    # ── Overall ──────────────────────────────────────────────────────────
    overall_result = fields.Selection([
        ('pass', 'Pass'),
        ('pass_with_remarks', 'Pass with Remarks'),
        ('fail', 'Fail'),
    ], string='Overall Result', compute='_compute_overall_result',
        store=True, tracking=True)
    recommendations = fields.Text(string='Recommendations / Follow-up')
    escalate_to_head = fields.Boolean(
        string='Escalate to Head of Operation', default=False, tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
    ], default='draft', string='Status', tracking=True)

    # ── Compute helpers ──────────────────────────────────────────────────
    @api.depends('session_id')
    def _compute_program_id(self):
        for rec in self:
            if rec.session_id and rec.session_id.program_id:
                rec.program_id = rec.session_id.program_id
            elif not rec.program_id:
                rec.program_id = False

    _FAIL_SCORES = {'fail', 'major'}
    _MINOR_SCORES = {'minor'}

    @api.depends('child_safety_score', 'curriculum_score', 'facility_score')
    def _compute_overall_result(self):
        for rec in self:
            scores = {rec.child_safety_score, rec.curriculum_score, rec.facility_score}
            if scores & rec._FAIL_SCORES:
                rec.overall_result = 'fail'
            elif scores & rec._MINOR_SCORES:
                rec.overall_result = 'pass_with_remarks'
            else:
                rec.overall_result = 'pass'

    # ── Auto-escalate on fail ────────────────────────────────────────────
    @api.onchange('overall_result')
    def _onchange_overall_result(self):
        if self.overall_result == 'fail':
            self.escalate_to_head = True

    # ── Sequence assignment on create ────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name == 'New':
                rec.name = self.env['ir.sequence'].next_by_code('sfk.compliance.check') or 'New'
        return records

    # ── State transitions ────────────────────────────────────────────────
    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise exceptions.UserError('Only draft checks can be submitted.')
        self.write({'state': 'submitted'})

    def action_mark_reviewed(self):
        for rec in self:
            if rec.state != 'submitted':
                raise exceptions.UserError('Only submitted checks can be marked as reviewed.')
        self.write({'state': 'reviewed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
