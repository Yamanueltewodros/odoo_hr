# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SfkRoom(models.Model):
    _name = 'sfk.room'
    _description = 'Room'
    _order = 'name'

    name = fields.Char(string='Room Name', required=True)
    capacity = fields.Integer(string='Capacity', default=20)
    company_id = fields.Many2one(
        'res.company', string='Branch/Center',
        default=lambda self: self.env.company, required=True
    )
    active = fields.Boolean(default=True)

    @api.constrains('capacity')
    def _check_capacity_positive(self):
        for r in self:
            if r.capacity <= 0:
                raise exceptions.ValidationError("Room capacity must be a positive number.")
