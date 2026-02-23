# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    exit_interview_ids = fields.One2many(
        'hr.exit.interview', 'employee_id',
        string="Exit Interviews"
    )
    exit_interview_count = fields.Integer(
        compute='_compute_exit_interview_count'
    )

    def _compute_exit_interview_count(self):
        for rec in self:
            rec.exit_interview_count = len(rec.exit_interview_ids)

    def action_view_exit_interviews(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Exit Interviews',
            'res_model': 'hr.exit.interview',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }


class HrResignation(models.Model):
    _inherit = 'hr.resignation'

    exit_interview_id = fields.Many2one(
        'hr.exit.interview', string="Exit Interview",
        compute='_compute_exit_interview', store=True
    )
    exit_interview_state = fields.Selection(
        related='exit_interview_id.state',
        string="Exit Interview Status"
    )
    exit_interview_count = fields.Integer(
        compute='_compute_exit_interview_count'
    )

    def _compute_exit_interview(self):
        for rec in self:
            interview = self.env['hr.exit.interview'].search([
                ('resignation_id', '=', rec.id)
            ], limit=1)
            rec.exit_interview_id = interview

    def _compute_exit_interview_count(self):
        for rec in self:
            rec.exit_interview_count = self.env['hr.exit.interview'].search_count([
                ('resignation_id', '=', rec.id)
            ])

    def action_view_exit_interview(self):
        interviews = self.env['hr.exit.interview'].search([
            ('resignation_id', '=', self.id)
        ])
        if len(interviews) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Exit Interview',
                'res_model': 'hr.exit.interview',
                'view_mode': 'form',
                'res_id': interviews.id,
                'context': {
                    'default_employee_id': self.employee_id.id,
                    'default_resignation_id': self.id,
                    'default_exit_reason': 'resignation',
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Exit Interviews',
            'res_model': 'hr.exit.interview',
            'view_mode': 'list,form',
            'domain': [('resignation_id', '=', self.id)],
            'context': {
                'default_employee_id': self.employee_id.id,
                'default_resignation_id': self.id,
                'default_exit_reason': 'resignation',
            },
        }

    def action_create_exit_interview(self):
        """Create a new exit interview linked to this resignation."""
        self.ensure_one()
        interview = self.env['hr.exit.interview'].create({
            'employee_id': self.employee_id.id,
            'resignation_id': self.id,
            'exit_reason': 'resignation',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Exit Interview',
            'res_model': 'hr.exit.interview',
            'view_mode': 'form',
            'res_id': interview.id,
        }

    def action_approve_resignation(self):
        """Override to require a completed exit interview before approval."""
        for rec in self:
            interview = self.env['hr.exit.interview'].search([
                ('resignation_id', '=', rec.id),
                ('state', '=', 'done'),
            ], limit=1)
            if not interview:
                raise ValidationError(
                    _('You must complete an Exit Interview before approving '
                      'the resignation of %s.\n\n'
                      'Please create and mark the exit interview as Done first.')
                    % rec.employee_id.name
                )
        return super().action_approve_resignation()