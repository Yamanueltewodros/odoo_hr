# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SfkPolicy(models.Model):
    """
    SFK Policy / Standards Manual with version control.
    The Head of R&S is responsible for keeping these updated after quarterly
    and annual audits and aligning them with legal requirements.
    """
    _name = 'sfk.policy'
    _description = 'SFK Policy / Standards Manual'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'category, name'
    _rec_name = 'display_name'

    name = fields.Char(string='Policy Title', required=True, tracking=True)
    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name', store=True
    )
    category = fields.Selection([
        ('child_safety', 'Child Safety & Ethics'),
        ('curriculum', 'Curriculum & Standards'),
        ('logistics', 'Logistics & Transportation'),
        ('resource', 'Resource Management'),
        ('hr', 'HR & Conduct'),
        ('compliance', 'Compliance & Audit'),
        ('other', 'Other'),
    ], string='Category', required=True, tracking=True)
    version = fields.Char(string='Version', default='1.0', tracking=True)
    effective_date = fields.Date(string='Effective Date', tracking=True)
    review_due_date = fields.Date(string='Next Review Due', tracking=True)
    owner_id = fields.Many2one(
        'res.users', string='Policy Owner',
        default=lambda self: self.env.user, tracking=True
    )
    company_id = fields.Many2one(
        'res.company', string='Branch',
        default=lambda self: self.env.company
    )
    description = fields.Html(string='Policy Content / Summary')
    document_url = fields.Char(string='Document Link (Drive/SharePoint URL)')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('under_review', 'Under Review'),
        ('superseded', 'Superseded'),
    ], string='Status', default='draft', tracking=True)

    revision_ids = fields.One2many('sfk.policy.revision', 'policy_id', string='Revision History')
    revision_count = fields.Integer(compute='_compute_revision_count', string='Revisions')
    acknowledgment_ids = fields.One2many('sfk.policy.acknowledgment', 'policy_id', string='Acknowledgments')
    acknowledgment_count = fields.Integer(compute='_compute_revision_count', string='Acknowledged By')

    @api.depends('name', 'version')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} (v{rec.version})" if rec.version else rec.name

    @api.depends('revision_ids', 'acknowledgment_ids')
    def _compute_revision_count(self):
        for rec in self:
            rec.revision_count = len(rec.revision_ids)
            rec.acknowledgment_count = len(rec.acknowledgment_ids)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_review(self):
        self.write({'state': 'under_review'})

    def action_supersede(self):
        self.write({'state': 'superseded'})

    def action_create_revision(self):
        """Create a new draft revision of this policy."""
        self.ensure_one()
        # Log the current version as a revision record
        self.env['sfk.policy.revision'].create({
            'policy_id': self.id,
            'version': self.version,
            'revised_by': self.env.uid,
            'revision_date': fields.Date.today(),
            'summary': f"Revision from v{self.version}",
        })
        # Bump version minor number
        try:
            parts = self.version.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            self.version = '.'.join(parts)
        except Exception:
            self.version = self.version + '.1'
        self.state = 'draft'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sfk.policy',
            'res_id': self.id,
            'view_mode': 'form',
        }


class SfkPolicyRevision(models.Model):
    _name = 'sfk.policy.revision'
    _description = 'Policy Revision History'
    _order = 'revision_date desc'

    policy_id = fields.Many2one('sfk.policy', required=True, ondelete='cascade')
    version = fields.Char(string='Version', required=True)
    revision_date = fields.Date(string='Revision Date', required=True)
    revised_by = fields.Many2one('res.users', string='Revised By', readonly=True)
    summary = fields.Text(string='Change Summary')
    change_reason = fields.Selection([
        ('quarterly_audit', 'Quarterly Audit Findings'),
        ('annual_audit', 'Annual Audit Findings'),
        ('legal', 'Legal / Regulatory Update'),
        ('best_practice', 'Best Practice Update'),
        ('incident', 'Incident / Non-conformance'),
        ('other', 'Other'),
    ], string='Reason for Change')


class SfkPolicyAcknowledgment(models.Model):
    """
    Records that a staff member has read and acknowledged a specific policy version.
    """
    _name = 'sfk.policy.acknowledgment'
    _description = 'Policy Acknowledgment'
    _order = 'acknowledgment_date desc'

    policy_id = fields.Many2one(
        'sfk.policy', string='Policy', required=True, ondelete='cascade'
    )
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    acknowledgment_date = fields.Date(
        string='Acknowledged On', default=fields.Date.context_today, required=True
    )
    policy_version = fields.Char(
        string='Version Acknowledged', related='policy_id.version', store=True
    )
    notes = fields.Char(string='Notes')

    _sql_constraints = [
        (
            'unique_employee_policy_version',
            'unique(policy_id, employee_id, policy_version)',
            'This employee has already acknowledged this version of the policy.'
        )
    ]
