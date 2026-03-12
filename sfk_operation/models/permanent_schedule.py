# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import timedelta, datetime


class SfkPermanentSchedule(models.Model):
    _name = 'sfk.permanent.schedule'
    _description = 'Permanent Class Schedule Template'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Description', compute='_compute_display_name', store=True
    )
    program_id = fields.Many2one(
        'sfk.program', string='Program',
        required=True, ondelete='cascade'
    )
    program_type = fields.Selection(
        related='program_id.program_type', store=True
    )
    term_id = fields.Many2one(
        'sfk.term', string='Term',
        required=True,
        domain="[('program_id', '=', program_id)]"
    )
    grade = fields.Char(string='Grade / Class', required=True)
    course_id = fields.Many2one(
        'sfk.course', string='Course',
        compute='_compute_course_id', store=True
    )
    lead_instructor_id = fields.Many2one(
        'hr.employee', string='Lead Instructor', required=True
    )
    assistant_instructor_id = fields.Many2one(
        'hr.employee', string='Assistant Instructor'
    )
    student_count = fields.Integer(string='Estimated Student Count')
    center_id = fields.Many2one(
        'res.company', string='Center',
        default=lambda self: self.env.company
    )
    weekday = fields.Selection([
        ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
        ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
    ], string='Weekday', required=True)
    start_time = fields.Float(string='Start Time', help='e.g. 14.5 for 14:30')
    end_time = fields.Float(string='End Time', help='e.g. 16.5 for 16:30')
    duration_hours = fields.Float(
        string='Duration (hrs)', compute='_compute_duration',
        store=True, readonly=False
    )
    room_id = fields.Many2one(
        'sfk.room', string='Room',
        domain="[('company_id', '=', center_id)]"
    )

    @api.depends('term_id', 'grade')
    def _compute_course_id(self):
        for rec in self:
            if rec.term_id and rec.grade:
                mapping = self.env['sfk.term.course'].search([
                    ('term_id', '=', rec.term_id.id),
                    ('grade', '=', rec.grade),
                ], limit=1)
                rec.course_id = mapping.course_id if mapping else False
            else:
                rec.course_id = False

    @api.depends('grade', 'course_id', 'weekday', 'term_id')
    def _compute_display_name(self):
        day_map = dict(self._fields['weekday'].selection)
        for rec in self:
            day = day_map.get(rec.weekday, '')
            course = rec.course_id.name if rec.course_id else 'No Course'
            rec.display_name = f"{rec.grade or ''} — {course} ({day})"

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.end_time and rec.start_time:
                rec.duration_hours = rec.end_time - rec.start_time
            else:
                rec.duration_hours = 0.0

    @api.onchange('start_time', 'duration_hours')
    def _onchange_end_time(self):
        if self.start_time and self.duration_hours:
            self.end_time = self.start_time + self.duration_hours

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for rec in self:
            if rec.end_time <= rec.start_time:
                raise exceptions.ValidationError(
                    "Schedule end time must be after start time."
                )

    def _next_date_from_weekday(self, start_dt, weekday_int):
        days_ahead = (weekday_int - start_dt.weekday() + 7) % 7
        return start_dt + timedelta(days=days_ahead)

    def generate_sessions(self, start_date, end_date):
        """Generate weekly sessions from this template between two dates (inclusive).
        Checks for conflicts before creating each session."""
        Session = self.env['sfk.session']
        start_dt = fields.Date.to_date(start_date) if isinstance(start_date, str) else start_date
        end_dt = fields.Date.to_date(end_date) if isinstance(end_date, str) else end_date

        created = 0
        skipped = 0

        for tmpl in self:
            if not tmpl.course_id:
                tmpl.program_id.message_post(
                    body=f"⚠️ Schedule '{tmpl.display_name}' skipped: "
                         f"no course mapped for grade '{tmpl.grade}' in term '{tmpl.term_id.name}'."
                )
                continue

            weekday_int = int(tmpl.weekday)
            current = tmpl._next_date_from_weekday(start_dt, weekday_int)

            while current <= end_dt:
                hour = int(tmpl.start_time)
                minute = int(round((tmpl.start_time - hour) * 60))
                start_datetime = datetime.combine(current, datetime.min.time()).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                end_datetime = start_datetime + timedelta(hours=tmpl.duration_hours)

                # Skip duplicates
                exists = Session.search([
                    ('program_id', '=', tmpl.program_id.id),
                    ('term_id', '=', tmpl.term_id.id),
                    ('course_id', '=', tmpl.course_id.id),
                    ('grade', '=', tmpl.grade),
                    ('start_datetime', '=', start_datetime),
                ], limit=1)
                if exists:
                    current += timedelta(days=7)
                    skipped += 1
                    continue

                # Room conflict check
                if tmpl.room_id:
                    room_conflict = Session.search([
                        ('room_id', '=', tmpl.room_id.id),
                        ('start_datetime', '<', end_datetime),
                        ('end_datetime', '>', start_datetime),
                        ('state', '!=', 'cancelled'),
                    ], limit=1)
                    if room_conflict:
                        tmpl.program_id.message_post(
                            body=f"⚠️ Room '{tmpl.room_id.name}' conflict on "
                                 f"{current.isoformat()} for '{tmpl.display_name}'. Session skipped."
                        )
                        current += timedelta(days=7)
                        skipped += 1
                        continue

                # Instructor conflict check
                for instr_id in filter(None, [
                    tmpl.lead_instructor_id.id,
                    tmpl.assistant_instructor_id.id
                ]):
                    instr_conflict = Session.search([
                        '|',
                        ('lead_instructor_id', '=', instr_id),
                        ('assistant_instructor_id', '=', instr_id),
                        ('start_datetime', '<', end_datetime),
                        ('end_datetime', '>', start_datetime),
                        ('state', '!=', 'cancelled'),
                    ], limit=1)
                    if instr_conflict:
                        instr = self.env['hr.employee'].browse(instr_id)
                        tmpl.program_id.message_post(
                            body=f"⚠️ Instructor '{instr.name}' conflict on "
                                 f"{current.isoformat()} for '{tmpl.display_name}'. Session skipped."
                        )
                        current += timedelta(days=7)
                        skipped += 1
                        break
                else:
                    Session.create({
                        'name': f"{tmpl.course_id.name} — {current.isoformat()}",
                        'program_id': tmpl.program_id.id,
                        'center_id': tmpl.center_id.id,
                        'term_id': tmpl.term_id.id,
                        'course_id': tmpl.course_id.id,
                        'grade': tmpl.grade,
                        'start_datetime': start_datetime,
                        'end_datetime': end_datetime,
                        'room_id': tmpl.room_id.id if tmpl.room_id else False,
                        'manager_id': tmpl.program_id.manager_id.id,
                        'supervisor_id': tmpl.program_id.supervisor_id.id,
                        'lead_instructor_id': tmpl.lead_instructor_id.id,
                        'assistant_instructor_id': tmpl.assistant_instructor_id.id if tmpl.assistant_instructor_id else False,
                    })
                    created += 1

                current += timedelta(days=7)

        return created, skipped
