{
    'name': 'HR Resignation',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Manages the resignation process of employees',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'mail',
        'hr_contract',
        # REMOVE 'hr_exit_interview' here!
    ],
   'data': [
    'security/groups.xml',
    'security/ir.model.access.csv',
    'security/record_rules.xml',        # ← add this
    'data/ir_sequence_data.xml',
    'views/hr_employee_views.xml',
    'views/hr_resignation_views.xml',
],
    'installable': True,
    'application': True,
    'auto_install': False,
}