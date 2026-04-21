from odoo import _, exceptions, fields, models


def get_google_maps_url(latitude, longitude):
    """Generate Google Maps URL from coordinates."""
    return f"https://maps.google.com?q={latitude},{longitude}"


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    # Check-in fields
    in_latitude = fields.Float(
        string="Check-in Latitude",
        digits=(10, 7),
        readonly=True,
        aggregator=None,
    )
    in_longitude = fields.Float(
        string="Check-in Longitude",
        digits=(10, 7),
        readonly=True,
        aggregator=None,
    )
    in_location = fields.Char(
        string="Check-in Location",
        readonly=True,
        help="Based on GPS coordinates if available or on IP address",
    )
    in_ip_address = fields.Char(
        string="Check-in IP Address",
        readonly=True,
    )
    in_browser = fields.Char(
        string="Check-in Browser",
        readonly=True,
    )
    in_mode = fields.Selection(
        string="Check-in Mode",
        selection=[
            ("kiosk", "Kiosk"),
            ("systray", "Systray"),
            ("manual", "Manual"),
            ("technical", "Technical"),
        ],
        readonly=True,
        default="manual",
    )
    
    # Check-out fields
    out_latitude = fields.Float(
        string="Check-out Latitude",
        digits=(10, 7),
        readonly=True,
        aggregator=None,
    )
    out_longitude = fields.Float(
        string="Check-out Longitude",
        digits=(10, 7),
        readonly=True,
        aggregator=None,
    )
    out_location = fields.Char(
        string="Check-out Location",
        readonly=True,
        help="Based on GPS coordinates if available or on IP address",
    )
    out_ip_address = fields.Char(
        string="Check-out IP Address",
        readonly=True,
    )
    out_browser = fields.Char(
        string="Check-out Browser",
        readonly=True,
    )
    out_mode = fields.Selection(
        string="Check-out Mode",
        selection=[
            ("kiosk", "Kiosk"),
            ("systray", "Systray"),
            ("manual", "Manual"),
            ("technical", "Technical"),
            ("auto_check_out", "Automatic Check-Out"),
        ],
        readonly=True,
        default="manual",
    )
    
    # Configuration
    device_tracking_enabled = fields.Boolean(
        related="employee_id.company_id.attendance_device_tracking",
        string="Device Tracking Enabled",
    )

    def copy(self, default=None):
        """Prevent duplication of attendance records."""
        raise exceptions.UserError(_("You cannot duplicate an attendance."))

    def action_in_attendance_maps(self):
        """Open Google Maps with check-in location."""
        self.ensure_one()
        if not self.in_latitude or not self.in_longitude:
            raise exceptions.UserError(_("No GPS coordinates available for check-in."))
        return {
            "type": "ir.actions.act_url",
            "url": get_google_maps_url(self.in_latitude, self.in_longitude),
            "target": "new",
        }

    def action_out_attendance_maps(self):
        """Open Google Maps with check-out location."""
        self.ensure_one()
        if not self.out_latitude or not self.out_longitude:
            raise exceptions.UserError(_("No GPS coordinates available for check-out."))
        return {
            "type": "ir.actions.act_url",
            "url": get_google_maps_url(self.out_latitude, self.out_longitude),
            "target": "new",
        }

