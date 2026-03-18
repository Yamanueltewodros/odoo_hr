from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Legacy single-program selector (kept for backward compatibility)
    discount_program_id = fields.Many2one(
        "sfk.sale.discount.program",
        string="Discount Program",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Select a discount program to apply on this sales order.",
    )
    # New: allow selecting multiple programs
    discount_program_ids = fields.Many2many(
        "sfk.sale.discount.program",
        "sfk_sale_order_discount_program_rel",
        "order_id",
        "program_id",
        string="Discount Programs",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Select one or more discount programs to apply on this sales order.",
        copy=False,
    )

    discount_program_status = fields.Selection(
        [
            ("none", "No Program"),
            ("valid", "Valid"),
            ("invalid", "Invalid"),
        ],
        compute="_compute_discount_program_status",
        store=False,
    )
    discount_program_message = fields.Char(
        compute="_compute_discount_program_status",
        store=False,
    )
    discount_program_last_applied = fields.Datetime(readonly=True, copy=False)

    @api.depends(
        "discount_program_id",
        "discount_program_ids",
        "partner_id",
        "date_order",
        "amount_untaxed",
        "order_line",
    )
    def _compute_discount_program_status(self):
        for order in self:
            programs = order._get_selected_discount_programs()
            if not programs:
                order.discount_program_status = "none"
                order.discount_program_message = ""
                continue

            invalid_msgs = []
            valid_count = 0
            for program in programs:
                ok, msg = program.check_applicability(order)
                if ok:
                    valid_count += 1
                else:
                    invalid_msgs.append("%s: %s" % (program.name, msg))

            if valid_count:
                order.discount_program_status = "valid"
                order.discount_program_message = (
                    _("Some programs will be skipped: %s") % " | ".join(invalid_msgs) if invalid_msgs else ""
                )
            else:
                order.discount_program_status = "invalid"
                order.discount_program_message = " | ".join(invalid_msgs) if invalid_msgs else _("No valid programs.")

    def _get_selected_discount_programs(self):
        self.ensure_one()
        programs = self.discount_program_ids
        if self.discount_program_id:
            programs |= self.discount_program_id
        return programs.sorted(key=lambda p: (-p.priority, (p._origin.id or 0)))

    @staticmethod
    def _combine_discounts(existing_percent, additional_percent):
        existing = max(0.0, min(100.0, float(existing_percent or 0.0)))
        additional = max(0.0, min(100.0, float(additional_percent or 0.0)))
        return min(100.0, round(existing + additional, 2))

    def _get_discount_eligible_lines(self, program):
        self.ensure_one()
        lines = self.order_line.filtered(lambda l: not l.display_type)

        if program.apply_on == "products":
            lines = lines.filtered(lambda l: l.product_id and l.product_id in program.product_ids)
        elif program.apply_on == "categories":
            lines = lines.filtered(
                lambda l: l.product_id
                and l.product_id.categ_id
                and l.product_id.categ_id in program.product_categ_ids
            )

        if not program.override_manual_discounts:
            lines = lines.filtered(
                lambda l: not (l.discount and not (l.sfk_discount_program_id or l.sfk_discount_program_ids))
            )

        return lines

    def _clear_program_discounts(self):
        for order in self:
            lines = order.order_line.filtered(
                lambda l: not l.display_type and (l.sfk_discount_program_id or l.sfk_discount_program_ids)
            )
            if not lines:
                continue
            if order.id:
                lines.with_context(sfk_apply_discount_program=True).write(
                    {"discount": 0.0, "sfk_discount_program_id": False, "sfk_discount_program_ids": [(5, 0, 0)]}
                )
            else:
                for line in lines:
                    line.discount = 0.0
                    line.sfk_discount_program_id = False
                    line.sfk_discount_program_ids = [(5, 0, 0)]

    def _apply_discount_program(self, interactive=False):
        for order in self:
            programs = order._get_selected_discount_programs()
            if not programs:
                order._clear_program_discounts()
                continue

            order._clear_program_discounts()

            invalid_msgs = []
            applied_any = False

            applicability = {}
            for program in programs:
                ok, msg = program.check_applicability(order)
                applicability[program.id] = (ok, msg)
                if not ok:
                    invalid_msgs.append("%s: %s" % (program.name, msg))

            for program in programs:
                ok, _msg = applicability.get(program.id, (False, ""))
                if not ok:
                    continue

                eligible_lines = order._get_discount_eligible_lines(program)
                if not eligible_lines:
                    continue

                if program.discount_type == "percent":
                    discount_percent = float(program.value)
                    for line in eligible_lines:
                        new_discount = order._combine_discounts(line.discount, discount_percent)
                        vals = {
                            "discount": new_discount,
                            "sfk_discount_program_id": program.id,
                            "sfk_discount_program_ids": [(4, program.id)],
                        }
                        if order.id:
                            line.with_context(sfk_apply_discount_program=True).write(vals)
                        else:
                            line.discount = new_discount
                            line.sfk_discount_program_id = program
                            line.sfk_discount_program_ids = [(4, program.id)]
                    applied_any = True

                else:
                    fixed_amount = float(program.value)
                    bases = []
                    total_base = 0.0
                    for line in eligible_lines:
                        # ✅ FIX APPLIED HERE ONLY
                        net_base = float(line.price_unit) * float(line.product_uom_qty)

                        if net_base <= 0:
                            continue
                        bases.append((line, net_base))
                        total_base += net_base

                    if total_base <= 0:
                        continue

                    fixed_to_apply = min(fixed_amount, total_base)
                    for line, net_base in bases:
                        share = fixed_to_apply * (net_base / total_base)
                        additional_percent = min(100.0, round((share / net_base) * 100.0, 2))
                        new_discount = order._combine_discounts(line.discount, additional_percent)
                        vals = {
                            "discount": new_discount,
                            "sfk_discount_program_id": program.id,
                            "sfk_discount_program_ids": [(4, program.id)],
                        }
                        if order.id:
                            line.with_context(sfk_apply_discount_program=True).write(vals)
                        else:
                            line.discount = new_discount
                            line.sfk_discount_program_id = program
                            line.sfk_discount_program_ids = [(4, program.id)]
                    applied_any = True

            if order.id and applied_any:
                order.discount_program_last_applied = fields.Datetime.now()

            if interactive and (invalid_msgs and applied_any):
                return {
                    "warning": {
                        "title": _("Some discounts were skipped"),
                        "message": " | ".join(invalid_msgs),
                    }
                }
            if interactive and (invalid_msgs and not applied_any):
                return {
                    "warning": {
                        "title": _("Discount not applied"),
                        "message": " | ".join(invalid_msgs),
                    }
                }

        return {}

    @api.onchange("discount_program_id")
    def _onchange_discount_program_id(self):
        for order in self:
            if order.discount_program_id and order.discount_program_id not in order.discount_program_ids:
                order.discount_program_ids = [(4, order.discount_program_id.id)]
        return self._apply_discount_program(interactive=True)

    @api.onchange("discount_program_ids")
    def _onchange_discount_program_ids(self):
        for order in self:
            programs = order.discount_program_ids.sorted(key=lambda p: (-p.priority, (p._origin.id or 0)))
            order.discount_program_id = programs[:1].id if programs else False
        return self._apply_discount_program(interactive=True)

    @api.onchange("partner_id", "date_order", "order_line")
    def _onchange_discount_program_recompute(self):
        if self.discount_program_id or self.discount_program_ids:
            return self._apply_discount_program(interactive=True)
        return {}

    def write(self, vals):
        res = super().write(vals)
        triggers = {"discount_program_id", "discount_program_ids", "partner_id", "date_order", "order_line"}
        if triggers.intersection(vals.keys()):
            for order in self:
                order._apply_discount_program(interactive=False)
        return res

    def action_confirm(self):
        for order in self:
            programs = order._get_selected_discount_programs()
            if programs:
                ok_any = False
                msgs = []
                for program in programs:
                    ok, msg = program.check_applicability(order)
                    if ok:
                        ok_any = True
                    else:
                        msgs.append("%s: %s" % (program.name, msg))
                if not ok_any:
                    raise UserError(_("Cannot confirm order: %(msg)s") % {"msg": " | ".join(msgs)})
                order._apply_discount_program(interactive=False)
        return super().action_confirm()