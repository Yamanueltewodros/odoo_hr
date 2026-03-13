from odoo import api, exceptions, fields, models
from odoo.tools import float_compare


class StockLocation(models.Model):
    _inherit = 'stock.location'

    sfk_responsible_employee_id = fields.Many2one('hr.employee', string='Responsible Employee')
    sfk_responsible_user_id = fields.Many2one(
        'res.users',
        related='sfk_responsible_employee_id.user_id',
        string='Responsible User',
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        for vals in vals_list:
            if vals.get('usage') == 'internal' and not vals.get('sfk_responsible_employee_id') and employee:
                vals['sfk_responsible_employee_id'] = employee.id
        return super().create(vals_list)


class SfkProgram(models.Model):
    _inherit = 'sfk.program'

    program_stock_location_id = fields.Many2one(
        'stock.location',
        string='Program Stock Location',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    material_transfer_ids = fields.One2many('sfk.program.material.transfer', 'program_id', string='Material Transfers')
    material_transfer_count = fields.Integer(compute='_compute_material_transfer_count', string='Transfers')

    @api.depends('material_transfer_ids')
    def _compute_material_transfer_count(self):
        for rec in self:
            rec.material_transfer_count = len(rec.material_transfer_ids)

    def action_view_material_transfers(self):
        self.ensure_one()
        action = self.env.ref('sfk_operation_inventory.sfk_material_transfer_action').read()[0]
        action['domain'] = [('program_id', '=', self.id)]
        action['context'] = {
            'default_program_id': self.id,
            'default_destination_location_id': self.program_stock_location_id.id,
        }
        return action

    def _default_program_source_location(self):
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        return warehouse.lot_stock_id if warehouse else False

    def _default_program_internal_picking_type(self):
        self.ensure_one()
        return self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

    def action_create_program_stock_location(self):
        for rec in self:
            if rec.program_stock_location_id:
                continue
            parent = rec._default_program_source_location()
            if not parent:
                raise exceptions.UserError('No warehouse stock location found for this branch.')
            responsible_employee = False
            if rec.manager_id:
                responsible_employee = self.env['hr.employee'].search(
                    [('user_id', '=', rec.manager_id.id)],
                    limit=1,
                )
            if not responsible_employee:
                responsible_employee = self.env['hr.employee'].search(
                    [('user_id', '=', self.env.user.id)],
                    limit=1,
                )
            location = self.env['stock.location'].create({
                'name': f"{rec.name} Materials",
                'location_id': parent.id,
                'usage': 'internal',
                'company_id': rec.company_id.id,
                'sfk_responsible_employee_id': responsible_employee.id if responsible_employee else False,
            })
            rec.program_stock_location_id = location.id


class SfkProgramMaterialTransfer(models.Model):
    _name = 'sfk.program.material.transfer'
    _description = 'Program Material Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(default='New', required=True, readonly=True, copy=False)
    program_id = fields.Many2one('sfk.program', required=True, ondelete='cascade', tracking=True)
    session_id = fields.Many2one('sfk.session', string='Session/Class', tracking=True)
    company_id = fields.Many2one('res.company', related='program_id.company_id', store=True, readonly=True)

    priority = fields.Selection([('0', 'Normal'), ('1', 'Urgent')], default='0')
    deadline = fields.Date()

    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    destination_location_id = fields.Many2one(
        'stock.location',
        required=True,
        string='Destination Location',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operation Type',
        domain="[('code', '=', 'internal'), ('company_id', '=', company_id)]",
        tracking=True,
    )

    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    requested_on = fields.Datetime(readonly=True)
    approved_by = fields.Many2one('res.users', readonly=True)
    approved_on = fields.Datetime(readonly=True)
    dispatched_by = fields.Many2one('res.users', readonly=True)
    dispatched_on = fields.Datetime(readonly=True)
    receipt_confirmed_by = fields.Many2one('res.users', readonly=True)
    receipt_confirmed_on = fields.Datetime(readonly=True)

    state = fields.Selection([
        ('draft', 'Draft Request'),
        ('approved', 'Approved'),
        ('dispatched', 'Dispatched'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    picking_id = fields.Many2one('stock.picking', readonly=True, copy=False)
    line_ids = fields.One2many('sfk.program.material.transfer.line', 'transfer_id', string='Materials')
    discrepancy_line_ids = fields.One2many('sfk.program.material.discrepancy.line', 'transfer_id', string='Discrepancies')
    discrepancy_report_id = fields.Many2one('sfk.program.material.discrepancy.report', readonly=True, copy=False)
    discrepancy_note = fields.Text()

    requested_total_qty = fields.Float(compute='_compute_qty_totals', string='Requested Total')
    approved_total_qty = fields.Float(compute='_compute_qty_totals', string='Approved Total')
    validated_total_qty = fields.Float(compute='_compute_qty_totals', string='Validated Total')
    request_approved_diff_total = fields.Float(compute='_compute_qty_totals', string='Req-Approved Diff')
    approved_validated_diff_total = fields.Float(compute='_compute_qty_totals', string='Approved-Validated Diff')

    @api.depends(
        'line_ids.product_uom_qty',
        'line_ids.approved_uom_qty',
        'line_ids.validated_uom_qty',
        'line_ids.request_approved_diff_qty',
        'line_ids.approved_validated_diff_qty',
    )
    def _compute_qty_totals(self):
        for rec in self:
            rec.requested_total_qty = sum(rec.line_ids.mapped('product_uom_qty'))
            rec.approved_total_qty = sum(rec.line_ids.mapped('approved_uom_qty'))
            rec.validated_total_qty = sum(rec.line_ids.mapped('validated_uom_qty'))
            rec.request_approved_diff_total = sum(rec.line_ids.mapped('request_approved_diff_qty'))
            rec.approved_validated_diff_total = sum(rec.line_ids.mapped('approved_validated_diff_qty'))

    def _is_source_responsible(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        return bool(self.source_location_id and self.source_location_id.sfk_responsible_user_id == user)

    def _is_destination_responsible(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        return bool(self.destination_location_id and self.destination_location_id.sfk_responsible_user_id == user)

    @api.onchange('program_id')
    def _onchange_program_id(self):
        for rec in self:
            if not rec.program_id:
                continue
            if rec.program_id.program_stock_location_id:
                rec.destination_location_id = rec.program_id.program_stock_location_id
            if not rec.picking_type_id:
                rec.picking_type_id = rec.program_id._default_program_internal_picking_type()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name == 'New':
                rec.name = f'TRF/{rec.id:05d}'
            if not rec.requested_on:
                rec.requested_on = fields.Datetime.now()
        return records

    def action_approve_request(self):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise exceptions.AccessError('Only Inventory Administrator can approve requests.')

        for rec in self:
            if rec.state != 'draft':
                raise exceptions.UserError('Only draft requests can be approved.')
            if not rec.line_ids:
                raise exceptions.UserError('Add at least one material line.')
            if not rec.destination_location_id:
                raise exceptions.UserError('Destination location is required.')
            if not rec.source_location_id:
                rec.source_location_id = rec.program_id._default_program_source_location()
            if not rec.source_location_id:
                raise exceptions.UserError('Set source location before approval.')
            if not rec.picking_type_id:
                rec.picking_type_id = rec.program_id._default_program_internal_picking_type()
            if not rec.picking_type_id:
                raise exceptions.UserError('No internal picking type found for this company.')

            has_positive_approved = False
            for line in rec.line_ids:
                if line.approved_uom_qty < 0:
                    raise exceptions.UserError('Approved quantity cannot be negative.')
                if line.approved_uom_qty > line.product_uom_qty:
                    raise exceptions.UserError(
                        f"Approved quantity cannot exceed requested quantity for {line.product_id.display_name}."
                    )
                if line.approved_uom_qty > 0:
                    has_positive_approved = True

            if not has_positive_approved:
                raise exceptions.UserError('At least one line must have approved quantity greater than zero.')

            if not rec.picking_id:
                rec.picking_id = rec._create_internal_picking_from_approved_qty()

            rec.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_on': fields.Datetime.now(),
            })

    def _create_internal_picking_from_approved_qty(self):
        self.ensure_one()
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.name,
            'company_id': self.company_id.id,
        })
        for line in self.line_ids.filtered(lambda l: l.approved_uom_qty > 0):
            move = self.env['stock.move'].create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.approved_uom_qty,
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': self.destination_location_id.id,
                'company_id': self.company_id.id,
            })
            line.move_id = move.id
        picking.action_confirm()
        picking.action_assign()
        return picking

    def action_confirm_dispatch(self):
        for rec in self:
            if rec.state != 'approved':
                raise exceptions.UserError('Only approved transfers can be dispatched.')
            if not (self.env.user.has_group('stock.group_stock_manager') or rec._is_source_responsible()):
                raise exceptions.AccessError('Only source location responsible or Inventory Administrator can confirm dispatch.')
            if not rec.picking_id:
                raise exceptions.UserError('No stock transfer is linked.')
            if rec.picking_id.state == 'cancel':
                raise exceptions.UserError('Cancelled transfer cannot be dispatched.')
            if rec.picking_id.state != 'done':
                raise exceptions.UserError(
                    'Validate the internal stock transfer first. '
                    'Dispatch confirmation is only allowed after validation.'
                )
            rec._ensure_discrepancy_lines()
            rec.write({
                'state': 'dispatched',
                'dispatched_by': self.env.user.id,
                'dispatched_on': fields.Datetime.now(),
            })

    def _get_or_create_damaged_location(self):
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
        parent = warehouse.lot_stock_id if warehouse else self.destination_location_id
        damaged = self.env['stock.location'].search([
            ('company_id', '=', self.company_id.id),
            ('usage', '=', 'internal'),
            ('name', '=', 'Damaged Materials'),
        ], limit=1)
        if not damaged:
            damaged = self.env['stock.location'].create({
                'name': 'Damaged Materials',
                'usage': 'internal',
                'company_id': self.company_id.id,
                'location_id': parent.id if parent else False,
            })
        return damaged

    def _create_damaged_transfer(self):
        self.ensure_one()
        damaged_lines = self.discrepancy_line_ids.filtered(lambda l: l.damaged_qty > 0)
        if not damaged_lines:
            return

        picking_type = self.picking_type_id or self.program_id._default_program_internal_picking_type()
        damaged_location = self._get_or_create_damaged_location()
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.destination_location_id.id,
            'location_dest_id': damaged_location.id,
            'origin': f'{self.name}/DAMAGED',
            'company_id': self.company_id.id,
        })

        for dline in damaged_lines:
            move = self.env['stock.move'].create({
                'name': f'Damaged - {dline.product_id.display_name}',
                'product_id': dline.product_id.id,
                'product_uom_qty': dline.damaged_qty,
                'product_uom': dline.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': self.destination_location_id.id,
                'location_dest_id': damaged_location.id,
                'company_id': self.company_id.id,
            })
            move._set_quantity_done(dline.damaged_qty)
            move.picked = True

        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()

    def _create_discrepancy_report(self):
        self.ensure_one()
        lines = []
        has_discrepancy = False
        for dline in self.discrepancy_line_ids:
            if dline.missing_qty > 0 or dline.damaged_qty > 0:
                has_discrepancy = True
            lines.append((0, 0, {
                'product_id': dline.product_id.id,
                'approved_qty': dline.approved_qty,
                'received_good_qty': dline.received_good_qty,
                'missing_qty': dline.missing_qty,
                'damaged_qty': dline.damaged_qty,
                'note': dline.note,
            }))

        if not has_discrepancy:
            return False

        report = self.env['sfk.program.material.discrepancy.report'].create({
            'transfer_id': self.id,
            'program_id': self.program_id.id,
            'reported_by': self.env.user.id,
            'reported_on': fields.Datetime.now(),
            'note': self.discrepancy_note,
            'line_ids': lines,
        })
        self.discrepancy_report_id = report.id
        return report

    def _ensure_discrepancy_lines(self):
        for rec in self:
            if rec.discrepancy_line_ids:
                continue
            lines = []
            for line in rec.line_ids.filtered(lambda l: l.approved_uom_qty > 0):
                lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'received_good_qty': line.approved_uom_qty,
                }))
            if lines:
                rec.discrepancy_line_ids = lines

    def action_confirm_receipt(self):
        for rec in self:
            if rec.state != 'dispatched':
                raise exceptions.UserError('Receipt can only be confirmed after dispatch confirmation.')
            if not (self.env.user.has_group('stock.group_stock_manager') or rec._is_destination_responsible()):
                raise exceptions.AccessError('Only destination location responsible or Inventory Administrator can confirm receipt.')
            if not rec.discrepancy_line_ids:
                rec._ensure_discrepancy_lines()
            for dline in rec.discrepancy_line_ids:
                if dline.received_good_qty < 0 or dline.missing_qty < 0 or dline.damaged_qty < 0:
                    raise exceptions.UserError('Received, missing, and damaged quantities cannot be negative.')
                total = dline.received_good_qty + dline.missing_qty + dline.damaged_qty
                if float_compare(
                    total,
                    dline.approved_qty,
                    precision_rounding=dline.product_id.uom_id.rounding,
                ) != 0:
                    raise exceptions.UserError(
                        f"Discrepancy totals for {dline.product_id.display_name} "
                        f"must equal approved quantity ({dline.approved_qty})."
                    )

            rec._create_damaged_transfer()
            rec._create_discrepancy_report()

            rec.write({
                'state': 'received',
                'receipt_confirmed_by': self.env.user.id,
                'receipt_confirmed_on': fields.Datetime.now(),
            })

    def action_cancel(self):
        for rec in self:
            if rec.state == 'received':
                raise exceptions.UserError('Received transfers cannot be cancelled from here.')
            if rec.picking_id and rec.picking_id.state not in ('done', 'cancel'):
                rec.picking_id.action_cancel()
            rec.state = 'cancelled'


class SfkProgramMaterialTransferLine(models.Model):
    _name = 'sfk.program.material.transfer.line'
    _description = 'Program Material Transfer Line'

    transfer_id = fields.Many2one('sfk.program.material.transfer', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True, domain="[('type', 'in', ('product', 'consu'))]")
    product_uom_qty = fields.Float(string='Requested Qty', required=True, default=1.0)
    approved_uom_qty = fields.Float(string='Approved Qty', default=0.0)
    product_uom_id = fields.Many2one('uom.uom', string='UoM', required=True)
    move_id = fields.Many2one('stock.move', readonly=True, copy=False)

    validated_uom_qty = fields.Float(compute='_compute_validation_fields', string='Validated Qty', store=True)
    request_approved_diff_qty = fields.Float(compute='_compute_validation_fields', string='Req-Approved Diff', store=True)
    approved_validated_diff_qty = fields.Float(compute='_compute_validation_fields', string='Approved-Validated Diff', store=True)

    @api.depends('product_uom_qty', 'approved_uom_qty', 'move_id.state', 'move_id.quantity')
    def _compute_validation_fields(self):
        for rec in self:
            validated = rec.move_id.quantity if rec.move_id and rec.move_id.state == 'done' else 0.0
            rec.validated_uom_qty = validated
            rec.request_approved_diff_qty = rec.product_uom_qty - rec.approved_uom_qty
            rec.approved_validated_diff_qty = rec.approved_uom_qty - validated

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id

    @api.onchange('product_uom_qty')
    def _onchange_requested_qty(self):
        if self.product_uom_qty and not self.approved_uom_qty:
            self.approved_uom_qty = self.product_uom_qty


class SfkProgramMaterialDiscrepancyLine(models.Model):
    _name = 'sfk.program.material.discrepancy.line'
    _description = 'Program Material Discrepancy Line'

    transfer_id = fields.Many2one('sfk.program.material.transfer', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    approved_qty = fields.Float(compute='_compute_qty', store=True)
    received_good_qty = fields.Float(default=0.0)
    missing_qty = fields.Float(default=0.0)
    damaged_qty = fields.Float(default=0.0)
    note = fields.Char()

    @api.depends('transfer_id.line_ids.product_id', 'transfer_id.line_ids.approved_uom_qty')
    def _compute_qty(self):
        for rec in self:
            line = rec.transfer_id.line_ids.filtered(lambda l: l.product_id == rec.product_id)[:1]
            rec.approved_qty = line.approved_uom_qty if line else 0.0

    @api.onchange('received_good_qty', 'damaged_qty', 'approved_qty')
    def _onchange_received_damaged(self):
        for rec in self:
            if rec.approved_qty:
                rec.missing_qty = max(rec.approved_qty - rec.received_good_qty - rec.damaged_qty, 0.0)


class SfkProgramMaterialDiscrepancyReport(models.Model):
    _name = 'sfk.program.material.discrepancy.report'
    _description = 'Material Discrepancy Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(default='New', required=True, readonly=True, copy=False)
    transfer_id = fields.Many2one('sfk.program.material.transfer', required=True, ondelete='cascade')
    program_id = fields.Many2one('sfk.program', required=True)
    company_id = fields.Many2one(related='program_id.company_id', store=True, readonly=True)
    reported_by = fields.Many2one('res.users', readonly=True)
    reported_on = fields.Datetime(readonly=True)
    state = fields.Selection([('open', 'Open'), ('resolved', 'Resolved')], default='open', tracking=True)
    note = fields.Text()
    line_ids = fields.One2many('sfk.program.material.discrepancy.report.line', 'report_id')
    missing_total = fields.Float(compute='_compute_totals')
    damaged_total = fields.Float(compute='_compute_totals')

    @api.depends('line_ids.missing_qty', 'line_ids.damaged_qty')
    def _compute_totals(self):
        for rec in self:
            rec.missing_total = sum(rec.line_ids.mapped('missing_qty'))
            rec.damaged_total = sum(rec.line_ids.mapped('damaged_qty'))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name == 'New':
                rec.name = f'DSC/{rec.id:05d}'
        return records

    def action_mark_resolved(self):
        self.write({'state': 'resolved'})


class SfkProgramMaterialDiscrepancyReportLine(models.Model):
    _name = 'sfk.program.material.discrepancy.report.line'
    _description = 'Material Discrepancy Report Line'

    report_id = fields.Many2one('sfk.program.material.discrepancy.report', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    approved_qty = fields.Float(default=0.0)
    received_good_qty = fields.Float(default=0.0)
    missing_qty = fields.Float(default=0.0)
    damaged_qty = fields.Float(default=0.0)
    note = fields.Char()
