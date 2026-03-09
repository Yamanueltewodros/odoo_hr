# Part of hr_attendance_geofence
import logging
from math import asin, cos, radians, sin, sqrt

from odoo import _, http
from odoo.http import request
from odoo.addons.hr_attendance.controllers.main import HrAttendance

_logger = logging.getLogger(__name__)


def _haversine_distance(lat1, lon1, lat2, lon2):
    """Return distance in metres between two GPS coordinates."""
    R = 6_371_000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    a = (sin((lat2 - lat1) / 2) ** 2
         + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2)
    return 2 * R * asin(sqrt(a))


def _check_geofence(company, latitude, longitude):
    """
    Returns (allowed: bool, error_message: str|None).
    - If geofence is disabled → always allowed.
    - If geofence is enabled but coords not configured → allowed (misconfiguration fallback).
    - If geofence is enabled and no GPS from client → blocked.
    - If outside radius → blocked with distance info.
    """
    if not company.attendance_geofence_enabled:
        return True, None

    if not (company.attendance_lat and company.attendance_lng):
        _logger.warning(
            "hr_attendance_geofence: geofence enabled for company %s "
            "but office coordinates not configured — skipping check.",
            company.name,
        )
        return True, None

    if not latitude or not longitude:
        return False, _(
            "Location access is required to check in/out. "
            "Please allow location permission on this device and try again."
        )

    dist = _haversine_distance(
        latitude, longitude,
        company.attendance_lat, company.attendance_lng,
    )

    if dist > company.attendance_radius:
        custom_msg = company.attendance_geofence_message or ""
        return False, _(
            "Check-in blocked: you are %(dist).0f m from the office "
            "(maximum allowed: %(radius).0f m). %(custom)s",
            dist=dist,
            radius=company.attendance_radius,
            custom=custom_msg,
        ).strip()

    return True, None


class AttendanceGeofenceController(HrAttendance):

    # ── Manual selection (PIN entry / employee picker) ───────────────────────
    # The kiosk already calls makeRpcWithGeolocation() for this route,
    # so latitude/longitude arrive here automatically.

    @http.route('/hr_attendance/manual_selection', type="json", auth="public")
    def manual_selection_with_geolocation(
        self, token, employee_id, pin_code,
        latitude=False, longitude=False,
    ):
        company = self._get_company(token)
        if not company:
            return {}

        allowed, error = _check_geofence(company, latitude, longitude)
        if not allowed:
            return {'geofence_error': error}

        return super().manual_selection_with_geolocation(
            token, employee_id, pin_code,
            latitude=latitude, longitude=longitude,
        )

    # ── Barcode / RFID scan ──────────────────────────────────────────────────
    # The standard scan_barcode() uses plain rpc() — no GPS is sent.
    # Our patched kiosk JS (attendance_geofence_kiosk.js) upgrades the call
    # to makeRpcWithGeolocation() so latitude/longitude arrive here.
    # We accept them as optional kwargs and validate before proceeding.

    @http.route('/hr_attendance/attendance_barcode_scanned', type="json", auth="public")
    def scan_barcode(self, token, barcode, latitude=False, longitude=False):
        company = self._get_company(token)
        if not company:
            return {}

        allowed, error = _check_geofence(company, latitude, longitude)
        if not allowed:
            # Return in the same shape the kiosk checks: no employee_name → show error
            return {'geofence_error': error}

        # Call the grandparent directly — super() would re-enter our override
        return HrAttendance.scan_barcode(self, token, barcode)

    # ── Geofence config endpoint (used by backend My Attendances button) ─────

    @http.route('/hr_attendance/geofence/config', type="json", auth="public")
    def geofence_config(self):
        company = request.env.user.company_id if not request.env.user._is_public() \
            else request.env['res.company'].sudo().search([], limit=1)
        return {
            'enabled':  company.attendance_geofence_enabled,
            'lat':      company.attendance_lat,
            'lng':      company.attendance_lng,
            'radius':   company.attendance_radius,
            'message':  company.attendance_geofence_message or '',
        }

    # ── Backend systray / My Attendances toggle ──────────────────────────────

    @http.route('/hr_attendance/geofence/toggle', type="json", auth="user")
    def geofence_toggle(self, lat=False, lng=False):
        employee = request.env.user.employee_id
        if not employee:
            return {'success': False, 'error': _('No employee linked to your account.')}

        company = employee.company_id
        allowed, error = _check_geofence(company, lat, lng)
        if not allowed:
            return {'success': False, 'error': error}

        geo = self._get_geoip_response('systray', latitude=lat, longitude=lng)
        employee._attendance_action_change(geo)
        state = employee.attendance_state  # 'checked_in' or 'checked_out'
        return {
            'success': True,
            'action': 'check_in' if state == 'checked_in' else 'check_out',
        }
