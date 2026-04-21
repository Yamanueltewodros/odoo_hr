{
    "name": "Attendance Device Tracking",
    "version": "18.0.1.0.0",
    "category": "Human Resources/Attendances",
    "summary": "Device and location tracking for employee attendances",
    "description": """
        Attendance Device Tracking
        ==========================
        Track device information and GPS location for employee check-ins and check-outs.
        
        Features:
        * GPS coordinates tracking for check-in/out
        * IP address and browser detection
        * Location name resolution
        * Integration with kiosk and systray modes
        * Google Maps integration for viewing locations
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "depends": ["hr_attendance", "base_geolocalize"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/hr_attendance_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "attendance_device_tracking/static/src/js/attendance_menu_patch.js",
        ],
        "hr_attendance.assets_public_attendance": [
            "attendance_device_tracking/static/src/js/public_kiosk_app_patch.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
