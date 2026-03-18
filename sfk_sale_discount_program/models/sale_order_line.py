from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sfk_discount_program_ids = fields.Many2many(
        "sfk.sale.discount.program",
        "sfk_sale_order_line_discount_program_rel",
        "order_line_id",
        "program_id",
        string="Discount Programs",
        readonly=True,
        copy=False,
    )
    sfk_discount_program_id = fields.Many2one(
        "sfk.sale.discount.program",
        string="Discount Program",
        readonly=True,
        copy=False,
    )

    def write(self, vals):
        if "discount" in vals and not self.env.context.get("sfk_apply_discount_program"):
            # User changed the discount manually: keep the discount but detach from program(s)
            program_lines = self.filtered(lambda l: l.sfk_discount_program_id or l.sfk_discount_program_ids)
            if program_lines:
                vals = dict(vals)
                vals["sfk_discount_program_id"] = False
                vals["sfk_discount_program_ids"] = [(5, 0, 0)]
        return super().write(vals)
