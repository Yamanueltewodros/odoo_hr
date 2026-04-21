from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    attendance_kiosk_url = fields.Char(
        related="company_id.attendance_kiosk_url",
        string="Kiosk URL",
        readonly=True,
    )
    attendance_device_tracking = fields.Boolean(
        related="company_id.attendance_device_tracking",
        string="Device & Location Tracking",
        readonly=False,
    )

