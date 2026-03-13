# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SfkStaffTraining(models.Model):
    """
    Staff training record aligned to the Head of R&S annual mandate:
    '100% of staff trained yearly on standards and safety.'
    Covers: child safety, ethics, compliance, curriculum standards.
    """
    _name = 'sfk.staff.training'
    _description = 'Staff Training Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'training_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Training Reference', required=True, readonly=True,
        default='New', copy=False
    )
    training_title = fields.Char(string='Training Title', required=True, tracking=True)
    training_type = fields.Selection([
        ('child_safety', 'Child Safety'),
        ('ethics', 'Ethics & Conduct'),
        ('compliance', 'Compliance & Standards'),
        ('curriculum', 'Curriculum Delivery'),
        ('resource_mgmt', 'Resource Management'),
        ('logistics', 'Logistics Procedures'),
        ('other', 'Other'),
    ], string='Training Type', required=True, tracking=True)
    training_date = fields.Date(
        string='Training Date', required=True,
        default=fields.Date.context_today, tracking=True
    )
    training_year = fields.Integer(
        string='Year', compute='_compute_year', store=True
    )
    facilitator_id = fields.Many2one('res.users', string='Facilitator')
    company_id = fields.Many2one(
        'res.company', string='Branch',
        default=lambda self: self.env.company
    )
    description = fields.Text(string='Training Description')
    materials_url = fields.Char(string='Training Materials Link')

    # Attendance
    participant_ids = fields.One2many(
        'sfk.staff.training.participant', 'training_id', string='Participants'
    )
    participant_count = fields.Integer(
        compute='_compute_participant_count', string='Participant Count'
    )
    certified_count = fields.Integer(
        compute='_compute_participant_count', string='Certified'
    )
    completion_rate = fields.Float(
        compute='_compute_participant_count', string='Completion %'
    )

    state = fields.Selection([
        ('planned', 'Planned'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planned', tracking=True)

    @api.depends('training_date')
    def _compute_year(self):
        for rec in self:
            rec.training_year = rec.training_date.year if rec.training_date else 0

    @api.depends('participant_ids', 'participant_ids.attended', 'participant_ids.certified')
    def _compute_participant_count(self):
        for rec in self:
            total = len(rec.participant_ids)
            attended = len(rec.participant_ids.filtered(lambda p: p.attended))
            certified = len(rec.participant_ids.filtered(lambda p: p.certified))
            rec.participant_count = total
            rec.certified_count = certified
            rec.completion_rate = (attended / total * 100) if total else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name == 'New':
                rec.name = self.env['ir.sequence'].next_by_code('sfk.staff.training') or 'New'
        return records

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class SfkStaffTrainingParticipant(models.Model):
    _name = 'sfk.staff.training.participant'
    _description = 'Training Participant'

    training_id = fields.Many2one(
        'sfk.staff.training', required=True, ondelete='cascade'
    )
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    attended = fields.Boolean(string='Attended', default=True)
    certified = fields.Boolean(string='Certified / Passed', default=False)
    notes = fields.Char(string='Notes')

    _sql_constraints = [
        (
            'unique_employee_training',
            'unique(training_id, employee_id)',
            'This employee is already listed in this training session.'
        )
    ]
