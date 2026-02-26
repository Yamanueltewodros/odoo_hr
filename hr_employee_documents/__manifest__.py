# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Documents',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Manage HR documents for employees with expiry tracking',
    'description': """
        HR Employee Documents
        =====================
        - Upload and manage employee documents
        - Track document expiry dates with visual highlights
        - Role-based access: HR Manager, HR Officer, Employee
        - Employees see only their own documents
        - Pre-loaded document types: Contract, ID Card, Medical Certificate
    """,
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'mail',
        'hr_contract',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/document_type_data.xml',
        'views/hr_employee_document_type_views.xml',
        'views/hr_employee_document_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
