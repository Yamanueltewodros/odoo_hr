import datetime

from requests.exceptions import RequestException

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.service.common import exp_version
from odoo.tools import float_round, py_to_js_locale
from odoo.tools.image import image_data_uri

from odoo.addons.hr_attendance.controllers.main import HrAttendance as HrAttendanceController


class HrAttendance(HrAttendanceController):
    """Extended HR Attendance controller with device tracking support."""

    @staticmethod
    def _get_user_attendance_data(employee):
        """Get basic attendance data for user display."""
        response = {}
        if employee:
            response = {
                "id": employee.id,
                "hours_today": float_round(employee.hours_today, precision_digits=2),
                "hours_previously_today": float_round(
                    employee.hours_previously_today, precision_digits=2
                ),
                "last_attendance_worked_hours": float_round(
                    employee.last_attendance_worked_hours, precision_digits=2
                ),
                "last_check_in": employee.last_check_in,
                "attendance_state": employee.attendance_state,
                "display_systray": employee.company_id.attendance_from_systray,
                "device_tracking_enabled": employee.company_id.attendance_device_tracking,
            }
        return response

    @staticmethod
    def _get_employee_info_response(employee):
        """Get complete employee information for kiosk display."""
        response = {}
        if employee:
            response = {
                **HrAttendance._get_user_attendance_data(employee),
                "employee_name": employee.name,
                "employee_avatar": employee.image_256 and image_data_uri(employee.image_256),
                "total_overtime": float_round(employee.total_overtime, precision_digits=2),
                "kiosk_delay": employee.company_id.attendance_kiosk_delay * 1000,
                "attendance": {
                    "check_in": employee.last_attendance_id.check_in,
                    "check_out": employee.last_attendance_id.check_out,
                },
                "overtime_today": sum(
                    request.env["hr.attendance.overtime.line"]
                    .sudo()
                    .search([
                        ("employee_id", "=", employee.id),
                        ("date", "=", datetime.date.today()),
                    ])
                    .mapped("duration")
                )
                or 0,
                "use_pin": employee.company_id.attendance_kiosk_use_pin,
                "display_overtime": employee.company_id.hr_attendance_display_overtime,
                "device_tracking_enabled": employee.company_id.attendance_device_tracking,
            }
        return response

    @staticmethod
    def _get_geoip_response(
        mode, latitude=False, longitude=False, device_tracking_enabled=True
    ):
        """
        Get geo-location information for attendance tracking.
        
        :param mode: Tracking mode (kiosk, systray, manual, technical)
        :param latitude: GPS latitude coordinate
        :param longitude: GPS longitude coordinate
        :param device_tracking_enabled: Whether device tracking is enabled
        :return: Dictionary with location data
        """
        response = {"mode": mode}
        if not device_tracking_enabled:
            return response
        
        # Get location name from coordinates or IP
        try:
            location = request.env["base.geocoder"]._get_localisation(latitude, longitude)
        except (UserError, RequestException):
            location = _("Unknown")
        
        # Compile geo information
        response.update({
            "location": location,
            "latitude": latitude or (
                request.geoip.location.latitude if request.geoip and request.geoip.location else False
            ),
            "longitude": longitude or (
                request.geoip.location.longitude if request.geoip and request.geoip.location else False
            ),
            "ip_address": request.geoip.ip if request.geoip else False,
            "browser": request.httprequest.user_agent.browser if request.httprequest.user_agent else False,
        })
        return response

    @http.route(["/hr_attendance/<token>"], type="http", auth="public", website=True, sitemap=True)
    def open_kiosk_mode(self, token, from_trial_mode=False):
        """Display the attendance kiosk mode interface."""
        company = self._get_company(token)
        if not company:
            return request.not_found()
        
        # Get departments for the company
        department_list = [
            {"id": dep["id"], "name": dep["name"], "count": dep["total_employee"]}
            for dep in request.env["hr.department"]
            .with_context(allowed_company_ids=[company.id])
            .sudo()
            .search_read(
                domain=[("company_id", "=", company.id)],
                fields=["id", "name", "total_employee"],
            )
        ]
        
        # Determine kiosk mode
        has_password = self.has_password()
        if not from_trial_mode and has_password:
            request.session.logout(keep_db=True)
        
        if from_trial_mode or (not has_password and not request.env.user.is_public):
            kiosk_mode = "settings"
        else:
            kiosk_mode = company.attendance_kiosk_mode
        
        version_info = exp_version()
        
        return request.render(
            "hr_attendance.public_kiosk_mode",
            {
                "kiosk_backend_info": {
                    "token": token,
                    "company_id": company.id,
                    "company_name": company.name,
                    "departments": department_list,
                    "kiosk_mode": kiosk_mode,
                    "from_trial_mode": from_trial_mode,
                    "barcode_source": company.attendance_barcode_source,
                    "device_tracking_enabled": company.attendance_device_tracking,
                    "lang": py_to_js_locale(company.partner_id.lang or company.env.lang),
                    "server_version_info": version_info.get("server_version_info"),
                },
            },
        )

    @http.route("/hr_attendance/attendance_employee_data", type="json", auth="public")
    def employee_attendance_data(self, token, employee_id):
        """Get employee attendance data for kiosk mode."""
        company = self._get_company(token)
        if company:
            employee = request.env["hr.employee"].sudo().browse(employee_id)
            if employee.company_id == company:
                return self._get_employee_info_response(employee)
        return {}

    @http.route("/hr_attendance/attendance_barcode_scanned", type="json", auth="public")
    def scan_barcode(self, token, barcode):
        """Handle barcode scan for attendance tracking."""
        company = self._get_company(token)
        if company:
            employee = request.env["hr.employee"].sudo().search([
                ("barcode", "=", barcode),
                ("company_id", "=", company.id),
            ], limit=1)
            if employee:
                employee._attendance_action_change(
                    self._get_geoip_response(
                        "kiosk",
                        device_tracking_enabled=company.attendance_device_tracking,
                    )
                )
                return self._get_employee_info_response(employee)
        return {}

    @http.route("/hr_attendance/manual_selection", type="json", auth="public")
    def manual_selection_with_geolocation(
        self, token, employee_id, pin_code, latitude=False, longitude=False
    ):
        """Handle manual employee selection for attendance tracking."""
        company = self._get_company(token)
        if company:
            employee = request.env["hr.employee"].sudo().browse(employee_id)
            if employee.company_id == company and (
                (not company.attendance_kiosk_use_pin) or (employee.pin == pin_code)
            ):
                employee.sudo()._attendance_action_change(
                    self._get_geoip_response(
                        "kiosk",
                        latitude=latitude,
                        longitude=longitude,
                        device_tracking_enabled=company.attendance_device_tracking,
                    )
                )
                return self._get_employee_info_response(employee)
        return {}

    def manual_selection(self, token, employee_id, pin_code, latitude=False, longitude=False):
        """Backward-compatible wrapper for manual selection calls."""
        return self.manual_selection_with_geolocation(
            token,
            employee_id,
            pin_code,
            latitude=latitude,
            longitude=longitude,
        )

    @http.route("/hr_attendance/systray_check_in_out", type="json", auth="user")
    def systray_attendance(self, latitude=False, longitude=False):
        """Handle check-in/out from systray menu."""
        employee = request.env.user.employee_id
        geo_ip_response = self._get_geoip_response(
            mode="systray",
            latitude=latitude,
            longitude=longitude,
            device_tracking_enabled=employee.company_id.attendance_device_tracking,
        )
        employee._attendance_action_change(geo_ip_response)
        return self._get_employee_info_response(employee)

    @http.route("/hr_attendance/attendance_user_data", type="json", auth="user", readonly=True)
    def user_attendance_data(self):
        """Get current user's attendance data."""
        employee = request.env.user.employee_id
        return self._get_user_attendance_data(employee)

    def has_password(self):
        """Check if current user has a password set."""
        request.env.cr.execute(
            """
            SELECT COUNT(password)
              FROM res_users
             WHERE id = %s
               AND password IS NOT NULL
             LIMIT 1
            """,
            (request.env.user.id,),
        )
        return bool(request.env.cr.fetchone()[0])
