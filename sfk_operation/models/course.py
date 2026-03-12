# -*- coding: utf-8 -*-
from odoo import models, fields


class SfkCourse(models.Model):
    _name = 'sfk.course'
    _description = 'Course'
    _order = 'name'

    name = fields.Char(string='Course Name', required=True)
    active = fields.Boolean(default=True)
