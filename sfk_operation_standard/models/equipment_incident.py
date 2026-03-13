# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SfkEquipmentIncident(models.Model):
    """
    Equipment loss, damage, or maintenance incident.
    The Head of R&S must ensure 100% of equipment incidents are documented
    and that losses/damage are reduced annually.
    Covers: laptops, robotics kits, projectors, dividers, chargers, accessories.
    """
    _name = 'sfk.equipment.incident'
    _description = 'Equipment Loss / Damage Incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'incident_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference', required=True, readonly=True,
        default='New', copy=False
    )
    incident_date = fields.Date(
        string='Incident Date', required=True,
        default=fields.Date.context_today, tracking=True
    )
    incident_type = fields.Selection([
        ('loss', 'Loss / Missing'),
        ('damage', 'Damage'),
        ('theft', 'Theft'),
        ('maintenance', 'Maintenance Required'),
    ], string='Incident Type', required=True, tracking=True)

    # Equipment details
    equipment_category = fields.Selection([
        ('laptop', 'Laptop'),
        ('robotics_kit', 'Robotics Kit'),
        ('projector', 'Projector'),
        ('divider', 'Divider'),
        ('charger', 'Charger'),
        ('accessory', 'Accessory'),
        ('other', 'Other'),
    ], string='Equipment Category', required=True)
    equipment_description = fields.Char(string='Equipment Description / Serial No.')
    quantity = fields.Integer(string='Quantity', default=1)
    estimated_value = fields.Float(string='Estimated Value (ETB)')

    program_id = fields.Many2one('sfk.program', string='Program', tracking=True)
    session_id = fields.Many2one('sfk.session', string='Session')
    company_id = fields.Many2one(
        'res.company', string='Branch',
        default=lambda self: self.env.company
    )
    reported_by = fields.Many2one(
        'res.users', string='Reported By',
        default=lambda self: self.env.user, readonly=True
    )
    responsible_staff_id = fields.Many2one(
        'hr.employee', string='Staff Responsible at Incident'
    )
    description = fields.Text(string='Incident Description', required=True)

    # Resolution
    action_taken = fields.Text(string='Corrective Action Taken')
    resolved_date = fields.Date(string='Resolved Date')
    replacement_cost = fields.Float(string='Replacement / Repair Cost (ETB)')
    cost_recovered = fields.Boolean(string='Cost Recovered from Staff', default=False)

    state = fields.Selection([
        ('reported', 'Reported'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='reported', tracking=True)

    escalate_to_head = fields.Boolean(string='Escalated to Head of Operation', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name == 'New':
                rec.name = self.env['ir.sequence'].next_by_code('sfk.equipment.incident') or 'New'
        return records

    def action_investigate(self):
        self.write({'state': 'investigating'})

    def action_resolve(self):
        for rec in self:
            if not rec.action_taken:
                raise exceptions.UserError('Please describe the corrective action before resolving.')
        self.write({'state': 'resolved', 'resolved_date': fields.Date.today()})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_escalate(self):
        for rec in self:
            rec.escalate_to_head = True
            rec.message_post(body='Incident escalated to Head of Operation.')
