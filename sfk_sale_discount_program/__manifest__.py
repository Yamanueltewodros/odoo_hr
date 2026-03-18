{
    "name": "SFK Sales Discount Programs",
    "summary": "Configurable discount programs for Sales Orders",
    "version": "18.0.1.0.0",
    "category": "Sales/Sales",
    "author": "SFK",
    "license": "LGPL-3",
    "depends": [
        "sale",
        "contacts",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/discount_program_rules.xml",
        "views/discount_program_views.xml",
        "views/sale_order_views.xml",
    ],
    "application": False,
    "installable": True,
}

