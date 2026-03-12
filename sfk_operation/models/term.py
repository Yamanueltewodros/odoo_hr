# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions


class SfkTerm(models.Model):
    _name = 'sfk.term'
    _description = 'Program Term'
    _order = 'start_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Term Name', required=True)
    program_id = fields.Many2one(
        'sfk.program', string='Program',
        required=True, ondelete='cascade'
    )
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    active = fields.Boolean(default=True)

    term_course_ids = fields.One2many(
        'sfk.term.course', 'term_id',
        string='Grade / Course Mapping'
    )

    @api.constrains('start_date', 'end_date', 'program_id')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                if rec.start_date >= rec.end_date:
                    raise exceptions.ValidationError(
                        "Term end date must be after start date."
                    )
                prog = rec.program_id
                if prog.start_date and rec.start_date < prog.start_date:
                    raise exceptions.ValidationError(
                        f"Term start date cannot be before program start date ({prog.start_date})."
                    )
                if prog.end_date and rec.end_date > prog.end_date:
                    raise exceptions.ValidationError(
                        f"Term end date cannot be after program end date ({prog.end_date})."
                    )


class SfkTermCourse(models.Model):
    _name = 'sfk.term.course'
    _description = 'Term Grade-to-Course Mapping'

    term_id = fields.Many2one('sfk.term', required=True, ondelete='cascade')
    course_id = fields.Many2one('sfk.course', string='Course', required=True)
    grade = fields.Char(string='Grade / Class', required=True)

    _sql_constraints = [
        (
            'term_grade_unique',
            'unique(term_id, grade)',
            'A course is already assigned to this grade in this term.'
        )
    ]
