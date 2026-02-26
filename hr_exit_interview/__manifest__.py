{
    'name': 'HR Exit Interview',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Handles exit interviews after employee resignations',
    'license': 'LGPL-3',
    'depends': [
        'hr_resignation',
        'mail',
        'hr',
    ],
  'data': [
    'security/exit_groups.xml',
    'security/ir.model.access.csv',
    'security/record_rules.xml',        # ← add this
    'data/sequence.xml',
    'views/hr_exit_interview_views.xml',
],
    'installable': True,
    'application': True,
    'auto_install': False,
}