from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SfkSaleDiscountProgram(models.Model):
    _name = "sfk.sale.discount.program"
    _description = "Sales Discount Program"
    _order = "priority desc, name, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)

    discount_type = fields.Selection(
        [
            ("percent", "Percentage"),
            ("fixed", "Fixed Amount"),
        ],
        required=True,
        default="percent",
    )
    value = fields.Float(required=True, help="Percent (0-100) or fixed amount in company currency.")

    date_start = fields.Date()
    date_end = fields.Date()

    partner_tag_ids = fields.Many2many(
        "res.partner.category",
        "sfk_discount_program_partner_tag_rel",
        "program_id",
        "tag_id",
        string="Customer Tags",
        help="Customer must have at least one of these tags.",
    )

    apply_on = fields.Selection(
        [
            ("all", "All Order Lines"),
            ("products", "Specific Products"),
            ("categories", "Product Categories"),
        ],
        required=True,
        default="all",
    )
    product_ids = fields.Many2many(
        "product.product",
        "sfk_discount_program_product_rel",
        "program_id",
        "product_id",
        string="Products",
    )
    product_categ_ids = fields.Many2many(
        "product.category",
        "sfk_discount_program_category_rel",
        "program_id",
        "categ_id",
        string="Product Categories",
    )

    min_order_amount = fields.Monetary(string="Minimum Untaxed Amount")
    min_total_qty = fields.Float(string="Minimum Total Quantity")

    override_manual_discounts = fields.Boolean(
        string="Override Manual Discounts",
        help="If enabled, the program can overwrite discounts that users manually entered on lines.",
        default=False,
    )

    priority = fields.Integer(default=10, help="Higher priority wins when stacking is implemented.")
    auto_apply = fields.Boolean(
        default=False,
        help="Reserved for future: automatically apply when conditions match.",
    )
    note = fields.Text(string="Internal Notes")

    @api.constrains("value", "discount_type")
    def _check_value(self):
        for rec in self:
            if rec.value <= 0:
                raise ValidationError(_("Discount value must be greater than 0."))
            if rec.discount_type == "percent" and rec.value > 100:
                raise ValidationError(_("Percentage discounts cannot exceed 100%."))

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(_("Start date must be before end date."))

    def _order_reference_date(self, order):
        date_order = order.date_order or fields.Datetime.now()
        return fields.Date.to_date(date_order)

    def check_applicability(self, order):
        self.ensure_one()
        if not self.active:
            return False, _("Discount program is inactive.")
        if self.company_id and order.company_id and self.company_id != order.company_id:
            return False, _("Discount program is not available for this company.")

        ref_date = self._order_reference_date(order)
        if self.date_start and ref_date < self.date_start:
            return False, _("Discount program is not yet active.")
        if self.date_end and ref_date > self.date_end:
            return False, _("Discount program has expired.")

        if self.partner_tag_ids:
            partner_tags = order.partner_id.category_id
            if not (partner_tags & self.partner_tag_ids):
                return False, _("Customer is not eligible for this discount program.")

        if self.min_order_amount and order.amount_untaxed < self.min_order_amount:
            return (
                False,
                _("Order untaxed amount must be at least %(amount)s.")
                % {"amount": "%s %s" % (self.min_order_amount, self.currency_id.name)},
            )

        if self.min_total_qty:
            total_qty = sum(order.order_line.filtered(lambda l: not l.display_type).mapped("product_uom_qty"))
            if total_qty < self.min_total_qty:
                return False, _("Order quantity must be at least %(qty)s.") % {"qty": self.min_total_qty}

        eligible_lines = order._get_discount_eligible_lines(self)
        if not eligible_lines:
            return False, _("No order lines match this discount program.")

        return True, _("Discount program applied.")

