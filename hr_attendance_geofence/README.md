# HR Attendance Geofence (`hr_attendance_geofence`)

Restrict Odoo attendance check-in / check-out to a configurable GPS radius around the office.

---

## Features

| Feature | Detail |
|---------|--------|
| **Configurable radius** | Set the office latitude, longitude, and allowed radius (metres) in Settings |
| **Dual validation** | Client-side Haversine pre-check (fast UX) + server-side re-validation (anti-spoof) |
| **GPS data stored** | Check-in/out latitude, longitude, and distance from office saved on every record |
| **Custom message** | Configure the message shown when an employee is outside the geofence |
| **Reporting columns** | Optional "In Dist (m)" / "Out Dist (m)" columns in the Attendance list view |

---

## Installation

1. Copy the `hr_attendance_geofence` folder into your Odoo `addons` path.
2. Restart the Odoo server.
3. Go to **Apps → Update Apps List** and install **HR Attendance Geofence**.

---

## Configuration

1. Navigate to **Settings → Attendances**.
2. Enable **Attendance Geofence**.
3. Enter your office **Latitude** and **Longitude**.
   - Tip: right-click your building in [Google Maps](https://maps.google.com) to copy coordinates.
4. Set the **Allowed Radius** (default: 100 m).
5. Optionally customise the **Restriction Message**.
6. Click **Save**.

---

## How It Works

```
Employee clicks Check In/Out
        │
        ▼
Browser Geolocation API
  navigator.geolocation.getCurrentPosition()
        │
        ▼
Client-side Haversine check  ──── outside? ──► Show error notification (no server call)
        │ inside
        ▼
POST /hr_attendance/geofence/toggle  { lat, lng }
        │
        ▼
Server creates / closes hr.attendance record
        │
        ▼
@api.constrains re-runs Haversine (server-side, tamper-proof)
        │
        ├── inside radius ──► Record saved ✔
        └── outside radius ─► ValidationError raised, record rolled back ✗
```

---

## Requirements

- Odoo **17.0** (adjust `__manifest__.py` version string for 16/18).
- **HTTPS** — browsers block `navigator.geolocation` on plain HTTP.
- Users must grant **location permission** in their browser or mobile app.

---

## File Structure

```
hr_attendance_geofence/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── attendance_geofence.py   # JSON endpoints
├── models/
│   ├── __init__.py
│   ├── res_company.py           # Geofence config fields
│   └── hr_attendance.py        # GPS fields + Haversine constraint
├── security/
│   └── ir.model.access.csv
├── static/src/
│   ├── js/attendance_geofence.js   # OWL component
│   └── xml/attendance_geofence.xml # OWL template
└── views/
    ├── res_config_settings_views.xml
    └── hr_attendance_views.xml
```
