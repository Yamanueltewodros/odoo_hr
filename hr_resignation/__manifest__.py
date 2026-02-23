# -*- coding: utf-8 -*-
{
    'name': 'Open HRMS Resignation',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Manages the resignation process of employees',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'mail',
        'hr_contract',
        'hr_employee_updation',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/hr_employee_views.xml',
        'views/hr_resignation_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': True,
    'auto_install': False,
}