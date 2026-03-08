
{
    "name": "Advanced Inventory Reports",
    'version': '18.0.1.0.0',
    "category": 'Warehouse',
    "summary": """Helps to Manage different types of Inventory Reports like FSN
    Report, Out Of Stock Report, Inventory XYZ Report etc.""",
    "description": """Provides efficient management of various types of
    inventory reports, including FSN Reports, Out-of-Stock Reports to monitor
    and prevent inventory shortages, Inventory XYZ Reports for categorizing
    items based on value and volume, and other customizable reports tailored to 
    the specific needs of the business.""",
    "author": "Cybrosys Techno Solutions",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    "depends": ["stock", "purchase", "sale_management"],
    "data": ["security/ir.model.access.csv",
             "report/aging_report_views.xml",
             "report/fsn_report_views.xml",
             "report/xyz_report_views.xml",
             "report/fsn_xyz_report_views.xml",
             "report/out_of_stock_report_views.xml",
             "report/over_stock_report_views.xml",
             "report/age_breakdown_report_views.xml",
             "report/stock_movement_report_views.xml",
             "wizard/inventory_aging_report_views.xml",
             "wizard/inventory_aging_data_report_views.xml",
             "wizard/inventory_fsn_report_views.xml",
             "wizard/inventory_fsn_data_report_views.xml",
             "wizard/inventory_xyz_report_views.xml",
             "wizard/inventory_xyz_data_report_views.xml",
             "wizard/inventory_fsn_xyz_report_views.xml",
             "wizard/inventory_fsn_xyz_data_report_views.xml",
             "wizard/inventory_out_of_stock_report_views.xml",
             "wizard/inventory_out_of_stock_data_report_views.xml",
             "wizard/inventory_age_breakdown_report_views.xml",
             "wizard/inventory_over_stock_report_views.xml",
             "wizard/inventory_over_stock_data_report_views.xml",
             "wizard/inventory_stock_movement_report_views.xml",
             ],
    'assets': {
        'web.assets_backend': [
            'inventory_advanced_reports/static/src/js/action_manager.js']
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
