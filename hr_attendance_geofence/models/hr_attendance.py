from math import asin, cos, radians, sin, sqrt

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


# ── Haversine helper ────────────────────────────────────────────────────────

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in metres between two GPS points."""
    R = 6_371_000  # Earth radius in metres
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


# ── Model ───────────────────────────────────────────────────────────────────

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # GPS coordinates captured at check-in / check-out
    check_in_lat  = fields.Float(string='Check-in Latitude',   digits=(10, 7), readonly=True)
    check_in_lng  = fields.Float(string='Check-in Longitude',  digits=(10, 7), readonly=True)
    check_out_lat = fields.Float(string='Check-out Latitude',  digits=(10, 7), readonly=True)
    check_out_lng = fields.Float(string='Check-out Longitude', digits=(10, 7), readonly=True)

    # Computed distances — stored so they are searchable/reportable
    check_in_distance  = fields.Float(
        string='Check-in Distance (m)',
        digits=(10, 2),
        readonly=True,
        store=True,
        compute='_compute_distances',
    )
    check_out_distance = fields.Float(
        string='Check-out Distance (m)',
        digits=(10, 2),
        readonly=True,
        store=True,
        compute='_compute_distances',
    )

    # ── Computed distances (safe — no write inside constrains) ───────────────

    @api.depends(
        'check_in_lat', 'check_in_lng',
        'check_out_lat', 'check_out_lng',
        'employee_id.company_id.attendance_lat',
        'employee_id.company_id.attendance_lng',
    )
    def _compute_distances(self):
        for rec in self:
            company = rec.employee_id.company_id or self.env.company
            office_lat = company.attendance_lat
            office_lng = company.attendance_lng

            if office_lat and office_lng:
                if rec.check_in_lat or rec.check_in_lng:
                    rec.check_in_distance = round(
                        _haversine(rec.check_in_lat, rec.check_in_lng,
                                   office_lat, office_lng), 2)
                else:
                    rec.check_in_distance = 0.0

                if rec.check_out_lat or rec.check_out_lng:
                    rec.check_out_distance = round(
                        _haversine(rec.check_out_lat, rec.check_out_lng,
                                   office_lat, office_lng), 2)
                else:
                    rec.check_out_distance = 0.0
            else:
                rec.check_in_distance = 0.0
                rec.check_out_distance = 0.0

    # ── Geofence validation (validate only — no field writes here) ───────────

    @api.constrains('check_in_lat', 'check_in_lng', 'check_out_lat', 'check_out_lng')
    def _check_geofence(self):
        for rec in self:
            company = rec.employee_id.company_id or self.env.company
            if not company.attendance_geofence_enabled:
                continue
            if not (company.attendance_lat and company.attendance_lng):
                continue  # geofence centre not configured yet

            # Validate check-in position
            if rec.check_in_lat or rec.check_in_lng:
                dist = _haversine(
                    rec.check_in_lat, rec.check_in_lng,
                    company.attendance_lat, company.attendance_lng,
                )
                if dist > company.attendance_radius:
                    raise ValidationError(
                        _(
                            "Check-in blocked: you are %(dist).0f m away from the office "
                            "(allowed radius: %(radius).0f m).\n%(msg)s",
                            dist=dist,
                            radius=company.attendance_radius,
                            msg=company.attendance_geofence_message or '',
                        )
                    )

            # Validate check-out position
            if rec.check_out_lat or rec.check_out_lng:
                dist = _haversine(
                    rec.check_out_lat, rec.check_out_lng,
                    company.attendance_lat, company.attendance_lng,
                )
                if dist > company.attendance_radius:
                    raise ValidationError(
                        _(
                            "Check-out blocked: you are %(dist).0f m away from the office "
                            "(allowed radius: %(radius).0f m).\n%(msg)s",
                            dist=dist,
                            radius=company.attendance_radius,
                            msg=company.attendance_geofence_message or '',
                        )
                    )
