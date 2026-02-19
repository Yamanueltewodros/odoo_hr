from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta


class HRDisciplinaryCase(models.Model):
    _name = "hr.disciplinary.case"
    _description = "Disciplinary Case"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "incident_date desc"

    # ─────────────────────────────────────────────
    # Identification
    # ─────────────────────────────────────────────
    name = fields.Char(default="New", readonly=True, copy=False, tracking=True,
                       string="Case Reference")
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    department_id = fields.Many2one(related="employee_id.department_id", store=True, readonly=True)
    position = fields.Char(related="employee_id.job_title", store=True, readonly=True)
    manager_id = fields.Many2one(related="employee_id.parent_id", store=True, readonly=True,
                                 string="Direct Manager")

    # ─────────────────────────────────────────────
    # Incident Details
    # ─────────────────────────────────────────────
    incident_date = fields.Date(required=True, tracking=True)
    reported_date = fields.Date(default=fields.Date.today, required=True)
    description = fields.Text(required=True, string="Incident Description")
    offense_classification_id = fields.Many2one("hr.offense.classification", required=True,
                                                tracking=True)
    severity_level = fields.Selection(related="offense_classification_id.severity_level",
                                      store=True, readonly=True)
    is_immediate_dismissal = fields.Boolean(
        related="offense_classification_id.is_immediate_dismissal", store=True, readonly=True)
    labour_law_article = fields.Selection([
        ('art_27', 'Article 27 - Termination Without Notice'),
        ('art_28', 'Article 28 - Termination With Notice'),
        ('progressive', 'Progressive Discipline'),
    ], string="Labour Law Basis", tracking=True)

    # ─────────────────────────────────────────────
    # Workflow State
    # ─────────────────────────────────────────────
    state = fields.Selection([
        ('draft',          'Draft'),
        ('notified',       'Notified'),
        ('show_cause',     'Show Cause'),
        ('investigation',  'Investigation'),
        ('hearing',        'Hearing'),
        ('decision',       'Decision'),
        ('appeal',         'Appeal'),
        ('closed',         'Closed'),
    ], default='notified', tracking=True, string="Stage")

    # ─────────────────────────────────────────────
    # Employee Acknowledgment (after notification)
    # ─────────────────────────────────────────────
    acknowledgment_state = fields.Selection([
        ('pending',       'Awaiting Response'),
        ('acknowledged',  'Acknowledged'),
        ('contested',     'Contested'),
    ], default='pending', tracking=True, string="Employee Response")

    acknowledged_date = fields.Date(readonly=True)
    contest_reason = fields.Text(string="Contest Statement",
                                 help="Employee's written statement disputing the facts of this case")
    contest_date = fields.Date(readonly=True)

    # ─────────────────────────────────────────────
    # Show Cause
    # ─────────────────────────────────────────────
    show_cause_issued_date = fields.Date()
    show_cause_deadline = fields.Date(string="Response Deadline")
    show_cause_response = fields.Text(string="Employee's Written Response")
    show_cause_responded = fields.Boolean(default=False)

    # ─────────────────────────────────────────────
    # Hearing
    # ─────────────────────────────────────────────
    hearing_date = fields.Date()
    hearing_notes = fields.Text()
    hearing_officer_id = fields.Many2one("hr.employee", string="Presiding Officer")

    # ─────────────────────────────────────────────
    # Decision (recorded by HR after hearing)
    # ─────────────────────────────────────────────
    decision_date = fields.Date(readonly=True)
    decision_by = fields.Many2one("res.users", readonly=True, string="Decision By")
    decision_outcome = fields.Selection([
        ('cleared',         'Cleared / No Action'),
        ('verbal_warning',  'Verbal Warning'),
        ('written_warning', 'Written Warning'),
        ('final_warning',   'Final Warning'),
        ('suspension',      'Suspension'),
        ('demotion',        'Demotion'),
        ('termination',     'Termination'),
    ], tracking=True, string="Decision Outcome")
    decision_rationale = fields.Text(string="Decision Rationale",
                                     help="Explain the reasoning behind this decision")

    # Suspension details (if decision = suspension)
    suspension_days = fields.Integer(string="Suspension Duration (days)")
    suspension_with_pay = fields.Boolean(string="With Pay?", default=False)

    # Termination details (if decision = termination)
    termination_type = fields.Selection([
        ('without_notice', 'Without Notice (Art. 27)'),
        ('with_notice',    'With Notice (Art. 28)'),
    ], string="Termination Type")
    notice_period_months = fields.Integer(
        string="Notice Period (months)",
        help="Art. 28: < 1yr = 1 month, 1-9 yrs = 2 months, > 9 yrs = 3 months"
    )

    # Decision served to employee
    decision_served = fields.Boolean(default=False, string="Decision Served to Employee?",
                                     tracking=True)
    decision_served_date = fields.Date(string="Served On")
    decision_served_method = fields.Selection([
        ('personal',     'Personal Delivery with Signature'),
        ('refused',      'Refused - Witness Noted'),
        ('postal',       'Sent to Last Known Address'),
        ('notice_board', 'Posted on Notice Board (10 days)'),
    ], string="Delivery Method")

    # ─────────────────────────────────────────────
    # Notice Delivery (Art. 14)
    # ─────────────────────────────────────────────
    notice_delivery_method = fields.Selection([
        ('personal',     'Personal Delivery with Signature'),
        ('refused',      'Refused - Witness Noted'),
        ('postal',       'Sent to Last Known Address'),
        ('notice_board', 'Posted on Notice Board (10 days)'),
    ], string="Initial Notice Delivery")
    notice_witness_id = fields.Many2one("res.users", string="Witness")
    notice_board_posted_date = fields.Date()
    notice_board_removal_date = fields.Date(
        compute="_compute_notice_board_removal", store=True)

    # ─────────────────────────────────────────────
    # Time Limits (Art. 18)
    # ─────────────────────────────────────────────
    employer_knowledge_date = fields.Date(
        string="Date Employer Became Aware",
        help="30 working-day employer action deadline starts here (Article 18)")
    employer_deadline = fields.Date(
        compute="_compute_employer_deadline", store=True,
        string="Employer Action Deadline (30 WD)")
    is_time_barred = fields.Boolean(compute="_compute_is_time_barred", store=True)

    # ─────────────────────────────────────────────
    # Absence Tracking (Art. 27)
    # ─────────────────────────────────────────────
    unauthorized_absence_days = fields.Integer(string="Unauthorized Absence Days (last 6 months)")
    late_arrival_count = fields.Integer(string="Late Arrivals (last 6 months)")
    absence_warnings_issued = fields.Boolean(string="Written Warnings Issued for Each Absence?")

    # ─────────────────────────────────────────────
    # Related Records
    # ─────────────────────────────────────────────
    investigation_ids = fields.One2many("hr.disciplinary.investigation", "case_id",
                                        string="Investigations")
    appeal_ids = fields.One2many("hr.disciplinary.appeal", "case_id", string="Appeals")

    # ─────────────────────────────────────────────
    # Progressive Discipline
    # ─────────────────────────────────────────────
    prior_case_count = fields.Integer(compute="_compute_prior_cases", string="Prior Cases")
    verbal_warning_count = fields.Integer(compute="_compute_warning_counts")
    written_warning_count = fields.Integer(compute="_compute_warning_counts")
    final_warning_count = fields.Integer(compute="_compute_warning_counts")
    recommended_action = fields.Selection([
        ('verbal_warning',       'Verbal Warning'),
        ('written_warning',      'Written Warning'),
        ('final_warning',        'Final Warning'),
        ('suspension',           'Suspension'),
        ('termination_notice',   'Termination with Notice (Art. 28)'),
        ('termination_no_notice','Termination without Notice (Art. 27)'),
    ], compute="_compute_recommended_action", store=True, string="Recommended Action")

    # ─────────────────────────────────────────────
    # Closure / Final Settlement (Art. 19)
    # ─────────────────────────────────────────────
    closure_date = fields.Date()
    closure_summary = fields.Text()
    final_payment_due_date = fields.Date(compute="_compute_final_payment_due", store=True)
    final_payment_completed = fields.Boolean(default=False)
    employment_certificate_issued = fields.Boolean(default=False)
    severance_applicable = fields.Boolean(default=False)
    severance_amount = fields.Float()
    warning_expiry_date = fields.Date(
        string="Warning Expiry Date",
        help="Date after which this warning is no longer active for progressive discipline"
    )

    # ─────────────────────────────────────────────
    # Computed fields
    # ─────────────────────────────────────────────
    @api.depends('notice_board_posted_date')
    def _compute_notice_board_removal(self):
        for rec in self:
            rec.notice_board_removal_date = (
                rec.notice_board_posted_date + timedelta(days=10)
                if rec.notice_board_posted_date else False)

    @api.depends('employer_knowledge_date')
    def _compute_employer_deadline(self):
        for rec in self:
            rec.employer_deadline = (
                rec.employer_knowledge_date + timedelta(days=42)
                if rec.employer_knowledge_date else False)

    @api.depends('employer_deadline', 'state')
    def _compute_is_time_barred(self):
        today = date.today()
        open_states = ['draft','notified','show_cause','investigation','hearing']
        for rec in self:
            rec.is_time_barred = bool(
                rec.employer_deadline and rec.employer_deadline < today
                and rec.state in open_states)

    @api.depends('closure_date', 'state')
    def _compute_final_payment_due(self):
        for rec in self:
            rec.final_payment_due_date = (
                rec.closure_date + timedelta(days=10)
                if rec.closure_date and rec.state == 'closed' else False)

    def _compute_prior_cases(self):
        for rec in self:
            rec.prior_case_count = self.search_count([
                ('employee_id', '=', rec.employee_id.id),
                ('id', '!=', rec.id),
                ('state', '=', 'closed'),
            ])

    def _compute_warning_counts(self):
        for rec in self:
            prior = self.search([
                ('employee_id', '=', rec.employee_id.id),
                ('id', '!=', rec.id),
                ('state', '=', 'closed'),
                ('decision_outcome', '!=', False),
            ])
            rec.verbal_warning_count = len(prior.filtered(
                lambda c: c.decision_outcome == 'verbal_warning'))
            rec.written_warning_count = len(prior.filtered(
                lambda c: c.decision_outcome == 'written_warning'))
            rec.final_warning_count = len(prior.filtered(
                lambda c: c.decision_outcome == 'final_warning'))

    @api.depends('severity_level', 'is_immediate_dismissal',
                 'verbal_warning_count', 'written_warning_count', 'final_warning_count',
                 'unauthorized_absence_days', 'late_arrival_count', 'absence_warnings_issued')
    def _compute_recommended_action(self):
        for rec in self:
            if rec.is_immediate_dismissal:
                rec.recommended_action = 'termination_no_notice'
            elif rec.unauthorized_absence_days >= 5 and rec.absence_warnings_issued:
                rec.recommended_action = 'termination_no_notice'
            elif rec.late_arrival_count >= 8 and rec.absence_warnings_issued:
                rec.recommended_action = 'termination_no_notice'
            elif rec.final_warning_count >= 1:
                rec.recommended_action = 'termination_notice'
            elif rec.written_warning_count >= 1:
                rec.recommended_action = 'final_warning'
            elif rec.verbal_warning_count >= 1:
                rec.recommended_action = 'written_warning'
            elif rec.severity_level == 'gross':
                rec.recommended_action = 'termination_no_notice'
            elif rec.severity_level == 'serious':
                rec.recommended_action = 'final_warning'
            elif rec.severity_level == 'moderate':
                rec.recommended_action = 'written_warning'
            else:
                rec.recommended_action = 'verbal_warning'

    # ─────────────────────────────────────────────
    # HR Workflow Actions
    # ─────────────────────────────────────────────
    def action_issue_show_cause(self):
        """Issue a Show Cause Notice — employee must explain their conduct."""
        self.ensure_one()
        if self.is_time_barred:
            raise UserError("This case is time-barred (30 working-day limit exceeded, Article 18).")
        self.write({
            'state': 'show_cause',
            'show_cause_issued_date': date.today(),
            'show_cause_deadline': date.today() + timedelta(days=5),
        })
        self.message_post(body=_(
            "Show Cause Notice issued. Employee must respond by <b>%s</b>."
        ) % self.show_cause_deadline)

    def action_record_show_cause_response(self):
        self.ensure_one()
        if not self.show_cause_response:
            raise UserError("Please record the employee's written response before confirming.")
        self.write({'show_cause_responded': True})
        self.message_post(body=_("Employee show cause response recorded."))

    def action_start_investigation(self):
        self.ensure_one()
        if self.is_time_barred:
            raise UserError("This case is time-barred (30 working-day limit exceeded, Article 18).")
        self.write({'state': 'investigation'})
        self.message_post(body=_("Case moved to Investigation."))

    def action_schedule_hearing(self):
        self.ensure_one()
        if not self.hearing_date:
            raise UserError("Please set a Hearing Date before scheduling the hearing.")
        self.write({'state': 'hearing'})
        self.message_post(body=_(
            "Disciplinary hearing scheduled for <b>%s</b>."
        ) % self.hearing_date)

    def action_move_to_decision(self):
        self.ensure_one()
        self.write({'state': 'decision'})
        self.message_post(body=_("Case moved to Decision stage. Please record the decision outcome."))

    def action_record_decision(self):
        """Record the formal disciplinary decision."""
        self.ensure_one()
        if not self.decision_outcome:
            raise UserError("Please select a Decision Outcome before recording.")
        if not self.decision_rationale:
            raise UserError("Please provide the Decision Rationale before recording.")
        if self.decision_outcome == 'termination' and not self.termination_type:
            raise UserError(
                "Please specify the termination type (with or without notice) before recording.")
        self.write({
            'decision_date': date.today(),
            'decision_by': self.env.user.id,
        })
        self.message_post(body=_(
            "Decision recorded by <b>%s</b>: <b>%s</b><br/>Rationale: %s"
        ) % (self.env.user.name,
             dict(self._fields['decision_outcome'].selection).get(self.decision_outcome),
             self.decision_rationale))

    def action_serve_decision(self):
        """Mark the decision as served to the employee — appeal window opens."""
        self.ensure_one()
        if not self.decision_outcome:
            raise UserError("Please record the decision outcome before serving it.")
        if not self.decision_served_method:
            raise UserError("Please select how the decision was delivered to the employee.")
        self.write({
            'decision_served': True,
            'decision_served_date': date.today(),
        })
        self.message_post(body=_(
            "Decision served to employee on <b>%s</b> via %s. "
            "Appeal window is now open (15 working days)."
        ) % (date.today(),
             dict(self._fields['decision_served_method'].selection).get(
                 self.decision_served_method)))

    def action_close_case(self):
        """Close the case — no appeal filed or appeal window expired."""
        self.ensure_one()
        if not self.decision_outcome:
            raise UserError("A decision must be recorded before closing the case.")
        self.write({
            'state': 'closed',
            'closure_date': date.today(),
        })
        self.message_post(body=_("Case closed on %s.") % date.today())

    def action_open_appeal(self):
        """Move to appeal stage — only after decision is served."""
        self.ensure_one()
        if not self.decision_served:
            raise UserError(
                "The decision must be served to the employee before an appeal can be filed. "
                "Please mark the decision as served first."
            )
        if self.decision_outcome == 'cleared':
            raise UserError(
                "The employee was cleared. There is no decision to appeal."
            )
        if self.acknowledgment_state == 'acknowledged' and self.state != 'decision':
            raise UserError(
                "The employee has acknowledged the case. Appeal is only available after a decision is served."
            )
        self.write({'state': 'appeal'})
        self.message_post(body=_("Case moved to Appeal stage."))

    # ─────────────────────────────────────────────
    # Employee Actions (run with sudo)
    # ─────────────────────────────────────────────
    def action_employee_acknowledge(self):
        self.ensure_one()
        self.sudo().write({
            'acknowledgment_state': 'acknowledged',
            'acknowledged_date': date.today(),
        })
        self.message_post(body=_(
            "Employee <b>%s</b> acknowledged receipt of this notice on %s."
        ) % (self.employee_id.name, date.today()))

    def action_employee_contest(self):
        self.ensure_one()
        contest_text = self.sudo().contest_reason
        if not contest_text:
            raise UserError(
                "Please write your contest statement in the text box above "
                "before clicking 'Contest This Case'."
            )
        self.sudo().write({
            'acknowledgment_state': 'contested',
            'contest_date': date.today(),
        })
        self.message_post(body=_(
            "Employee <b>%s</b> has <b>contested</b> this case on %s.<br/>"
            "<b>Statement:</b> %s"
        ) % (self.employee_id.name, date.today(), contest_text))

    # ─────────────────────────────────────────────
    # Create / Constraints
    # ─────────────────────────────────────────────
    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("hr.disciplinary.case") or "New")
        return super().create(vals)

    @api.constrains('incident_date', 'reported_date')
    def _check_dates(self):
        for rec in self:
            if rec.reported_date and rec.incident_date and rec.reported_date < rec.incident_date:
                raise ValidationError("Reported date cannot be before the incident date.")

    @api.onchange('decision_outcome')
    def _onchange_decision_outcome(self):
        if self.decision_outcome != 'termination':
            self.termination_type = False
            self.notice_period_months = 0
        if self.decision_outcome != 'suspension':
            self.suspension_days = 0
        # Auto-suggest notice period
        if self.decision_outcome == 'termination' and self.employee_id.first_contract_date:
            years = (date.today() - self.employee_id.first_contract_date).days / 365
            self.notice_period_months = 1 if years < 1 else (2 if years <= 9 else 3)