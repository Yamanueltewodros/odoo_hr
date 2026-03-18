from odoo.tests.common import SavepointCase


class TestSfkSaleDiscountProgram(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Parent Contact"})
        cls.tag_sibling = cls.env["res.partner.category"].create({"name": "Sibling Eligible"})
        cls.product_a = cls.env["product.product"].create({"name": "Course A", "list_price": 100.0})
        cls.product_b = cls.env["product.product"].create({"name": "Course B", "list_price": 200.0})

    def _make_order(self, partner=None, lines=None):
        partner = partner or self.partner
        lines = lines or [
            (0, 0, {"product_id": self.product_a.id, "product_uom_qty": 1, "price_unit": 100.0}),
            (0, 0, {"product_id": self.product_b.id, "product_uom_qty": 1, "price_unit": 200.0}),
        ]
        return self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": lines,
            }
        )

    def test_percent_discount_applies_when_tag_matches(self):
        self.partner.category_id = [(4, self.tag_sibling.id)]
        program = self.env["sfk.sale.discount.program"].create(
            {
                "name": "Sibling Discount",
                "discount_type": "percent",
                "value": 10.0,
                "partner_tag_ids": [(6, 0, [self.tag_sibling.id])],
            }
        )
        order = self._make_order()
        order.discount_program_ids = [(6, 0, [program.id])]
        order._apply_discount_program(interactive=False)
        self.assertEqual(order.order_line[0].discount, 10.0)
        self.assertEqual(order.order_line[1].discount, 10.0)

    def test_program_does_not_override_manual_discount_by_default(self):
        self.partner.category_id = [(4, self.tag_sibling.id)]
        program = self.env["sfk.sale.discount.program"].create(
            {
                "name": "Early Bird",
                "discount_type": "percent",
                "value": 15.0,
                "partner_tag_ids": [(6, 0, [self.tag_sibling.id])],
                "override_manual_discounts": False,
            }
        )
        order = self._make_order(
            lines=[
                (
                    0,
                    0,
                    {
                        "product_id": self.product_a.id,
                        "product_uom_qty": 1,
                        "price_unit": 100.0,
                        "discount": 5.0,
                    },
                ),
                (0, 0, {"product_id": self.product_b.id, "product_uom_qty": 1, "price_unit": 200.0}),
            ]
        )
        order.discount_program_ids = [(6, 0, [program.id])]
        order._apply_discount_program(interactive=False)
        self.assertEqual(order.order_line[0].discount, 5.0)
        self.assertEqual(order.order_line[1].discount, 15.0)

    def test_fixed_discount_distributes_proportionally(self):
        self.partner.category_id = [(4, self.tag_sibling.id)]
        program = self.env["sfk.sale.discount.program"].create(
            {
                "name": "Scholarship 30",
                "discount_type": "fixed",
                "value": 30.0,
                "partner_tag_ids": [(6, 0, [self.tag_sibling.id])],
            }
        )
        order = self._make_order()
        order.discount_program_ids = [(6, 0, [program.id])]
        order._apply_discount_program(interactive=False)
        self.assertEqual(order.order_line[0].discount, 10.0)
        self.assertEqual(order.order_line[1].discount, 10.0)

    def test_multiple_programs_can_apply(self):
        self.partner.category_id = [(4, self.tag_sibling.id)]
        program_a = self.env["sfk.sale.discount.program"].create(
            {
                "name": "Discount A",
                "discount_type": "percent",
                "value": 10.0,
                "partner_tag_ids": [(6, 0, [self.tag_sibling.id])],
                "apply_on": "products",
                "product_ids": [(6, 0, [self.product_a.id])],
                "priority": 20,
            }
        )
        program_b = self.env["sfk.sale.discount.program"].create(
            {
                "name": "Discount B",
                "discount_type": "percent",
                "value": 20.0,
                "partner_tag_ids": [(6, 0, [self.tag_sibling.id])],
                "apply_on": "products",
                "product_ids": [(6, 0, [self.product_b.id])],
                "priority": 10,
            }
        )
        order = self._make_order()
        order.discount_program_ids = [(6, 0, [program_a.id, program_b.id])]
        order._apply_discount_program(interactive=False)

        line_a = order.order_line.filtered(lambda l: l.product_id == self.product_a)
        line_b = order.order_line.filtered(lambda l: l.product_id == self.product_b)
        self.assertEqual(line_a.discount, 10.0)
        self.assertEqual(line_b.discount, 20.0)
        self.assertIn(program_a, line_a.sfk_discount_program_ids)
        self.assertIn(program_b, line_b.sfk_discount_program_ids)
