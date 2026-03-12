# -*- coding: utf-8 -*-
{
    'name': 'SFK Operations',
    'version': '18.0.1.0.0',
    'summary': 'STEM for Kids — Program, Session, Attendance & Student Management',
    'description': '''
        Core operational module for SFK:
        - Programs (Center-Based and School-Based)
        - Terms and Grade/Course mapping
        - Permanent Schedules (weekly template → session generation)
        - Sessions with instructor conflict & room conflict checks
        - Student enrollment and capacity management
        - Attendance tracking with eligibility validation
        - Role-based access: Instructor, Coordinator, Manager
    ''',
    'category': 'Operations',
    'author': 'Besufikad',
    'company': 'STEM for Kids Ethiopia',
    'website': 'https://www.odoo.com',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'security/sfk_operation_groups.xml',
        'security/ir.model.access.csv',
        'security/sfk_operation_security.xml',
        'data/sfk_sequence_data.xml',
        'views/course_views.xml',
        'views/room_views.xml',
        'views/term_views.xml',
        'views/student_views.xml',
        'views/session_views.xml',
        'views/program_views.xml',
        'views/attendance_views.xml',
        'views/permanent_schedule_views.xml',
        'views/menu_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
