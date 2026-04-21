import uuid
from urllib.parse import urljoin

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    attendance_kiosk_key = fields.Char(
        string="Attendance Kiosk Key",
        default=lambda self: uuid.uuid4().hex,
        copy=False,
        groups="hr_attendance.group_hr_attendance_officer",
        help="Unique key for accessing the attendance kiosk mode",
    )
    attendance_kiosk_url = fields.Char(
        string="Attendance Kiosk URL",
        compute="_compute_attendance_kiosk_url",
        help="Public URL for accessing the attendance kiosk",
    )
    attendance_device_tracking = fields.Boolean(
        string="Device & Location Tracking",
        default=False,
        help="Enable tracking of device information and GPS location during check-in/out",
    )

    @api.depends("attendance_kiosk_key")
    def _compute_attendance_kiosk_url(self):
        """Compute the public URL for the attendance kiosk."""
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for company in self:
            if company.attendance_kiosk_key:
                company.attendance_kiosk_url = urljoin(
                    base_url,
                    f"/hr_attendance/{company.attendance_kiosk_key}",
                )
            else:
                company.attendance_kiosk_url = False
