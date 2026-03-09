{
    'name': 'HR Attendance Geofence',
    'version': '18.0.1.0',
    'summary': 'Restrict check-in/out to a GPS radius around the office',
    'description': """
        Enforces a GPS geofence on all attendance check-in/out methods:
        - Kiosk manual selection (PIN / employee picker)
        - Kiosk barcode / RFID scan
        - Backend My Attendances button
        Uses browser Geolocation API + server-side Haversine validation.
    """,
    'category': 'Human Resources/Attendances',
    'author': 'Custom',
    'license': 'LGPL-3',

    'depends': ['base', 'hr', 'hr_attendance'],

    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/hr_attendance_views.xml',
    ],

    'assets': {
        # Backend — My Attendances geofence button
        'web.assets_backend': [
            'hr_attendance_geofence/static/src/js/attendance_geofence.js',
            'hr_attendance_geofence/static/src/xml/attendance_geofence.xml',
        ],
        # Public kiosk bundle — patches barcode scan and manual selection
        # to handle geofence errors returned by the server
        'hr_attendance.assets_public_attendance': [
            'hr_attendance_geofence/static/src/js/attendance_geofence_kiosk.js',
        ],
    },

    'installable': True,
    'application': False,
}
