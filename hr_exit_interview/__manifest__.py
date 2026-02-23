# -*- coding: utf-8 -*-
{
    'name': 'HR Exit Interview',
    'version': '18.0.1.0.0',
    'summary': 'Manage employee exit interviews before resignation approval',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr', 'hr_resignation'],
    'data': [
        'security/exit_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/hr_exit_interview_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
}