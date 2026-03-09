from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Geofence configuration ──────────────────────────────────────────────
    attendance_geofence_enabled = fields.Boolean(
        string='Enable Attendance Geofence',
        default=False,
        help='When enabled, employees must be within the allowed radius to check in/out.',
    )
    attendance_lat = fields.Float(
        string='Office Latitude',
        digits=(10, 7),
        help='Latitude of the office location used as the geofence centre.',
    )
    attendance_lng = fields.Float(
        string='Office Longitude',
        digits=(10, 7),
        help='Longitude of the office location used as the geofence centre.',
    )
    attendance_radius = fields.Float(
        string='Allowed Radius (m)',
        default=100.0,
        help='Maximum distance in metres an employee may be from the office to check in/out.',
    )
    attendance_geofence_message = fields.Char(
        string='Restriction Message',
        default='You are outside the allowed area. Please check in from the office.',
        help='Message shown to the employee when they are outside the geofence.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_geofence_enabled = fields.Boolean(
        related='company_id.attendance_geofence_enabled', readonly=False)
    attendance_lat = fields.Float(
        related='company_id.attendance_lat', readonly=False)
    attendance_lng = fields.Float(
        related='company_id.attendance_lng', readonly=False)
    attendance_radius = fields.Float(
        related='company_id.attendance_radius', readonly=False)
    attendance_geofence_message = fields.Char(
        related='company_id.attendance_geofence_message', readonly=False)
