# -*- coding: utf-8 -*-
{
    'name': 'SFK Operations Inventory',
    'version': '18.0.1.0.0',
    'summary': 'Material/stock management for SFK Operations',
    'description': '''
        Inventory and material control for SFK Operations:
        Requests, approvals, internal transfers, location responsibility,
        discrepancy handling, and reporting.
    ''',
    'category': 'Operations',
    'author': 'Besufikad',
    'company': 'STEM for Kids Ethiopia',
    'website': 'https://www.odoo.com',
    'depends': ['base', 'mail', 'stock', 'sfk_operation'],
    'data': [
        'security/sfk_operation_inventory_groups.xml',
        'security/ir.model.access.csv',
        'security/sfk_operation_inventory_security.xml',
        'views/stock_material_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
