# -*- coding: utf-8 -*-
{
    'name': 'SFK Operations Standard',
    'version': '18.0.2.0.0',
    'summary': 'Standards, compliance, audits, and resources oversight for SFK Operations',
    'description': '''
        Complete Standards & Resources module for the Head of Resources and Standards role:
        - Workshop compliance checks (Child Safety, Curriculum, Facility)
        - Audit management: weekly, quarterly, annual, special
        - Corrective Action Plans (CAP) linked to findings
        - Policy & Standards Manual with version control and staff acknowledgments
        - Equipment loss/damage/theft incident tracking
        - Staff training records with attendance and certification
        - Consolidated weekly reports with auto-aggregated KPIs
        - Role-based access: Standards Officer, Head of R&S, Operations Manager
    ''',
    'category': 'Operations',
    'author': 'Besufikad',
    'company': 'STEM for Kids Ethiopia',
    'website': 'https://www.odoo.com',
    'depends': ['base', 'mail', 'hr', 'sfk_operation'],
    'data': [
        'security/sfk_operation_standard_groups.xml',
        'security/ir.model.access.csv',
        'security/sfk_operation_standard_security.xml',
        'data/sfk_standard_sequence_data.xml',
        'views/compliance_check_views.xml',
        'views/audit_views.xml',
        'views/corrective_action_views.xml',
        'views/policy_views.xml',
        'views/equipment_incident_views.xml',
        'views/staff_training_views.xml',
        'views/weekly_report_views.xml',
        'views/menu_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
