# Attendance Device Tracking

## Overview

This module extends Odoo's HR Attendance functionality by adding device and location tracking capabilities for employee check-ins and check-outs.

## Features

### Device Tracking
- **IP Address Detection**: Automatically captures the IP address when employees check in/out
- **Browser Information**: Records the browser used for attendance
- **Mode Tracking**: Tracks how attendance was recorded (Kiosk, Systray, Manual, Technical, Auto Check-out)

### Location Tracking
- **GPS Coordinates**: Captures latitude and longitude when available
- **Location Name**: Automatically resolves GPS coordinates or IP addresses to location names
- **Google Maps Integration**: View check-in/out locations directly on Google Maps

## Installation

1. Place the module in your Odoo addons directory
2. Update the apps list: `Settings > Apps > Update Apps List`
3. Search for "Attendance Device Tracking"
4. Click Install

## Configuration

### Enable Device Tracking

1. Go to `Settings > HR Settings > Attendances`
2. Enable "Device & Location Tracking"
3. Save settings

### Access Modes

The module supports tracking across different attendance modes:

- **Kiosk Mode**: Public kiosk interface for employee check-in/out
- **Systray Mode**: Check-in/out from the user menu in Odoo interface
- **Manual Mode**: Manual attendance entries (no tracking)
- **Technical Mode**: Programmatic entries
- **Auto Check-out**: Automatic check-outs (tracked separately)

## Usage

### For Employees

#### Systray Check-in/out
1. Click the attendance icon in the top menu
2. If device tracking is enabled, you'll be prompted to allow location access
3. Click to check in or out
4. Your location and device information will be recorded

#### Kiosk Mode
1. Access the kiosk URL (provided by HR admin)
2. Select your profile or scan your badge
3. Enter PIN if required
4. If using GPS-enabled device, location will be captured automatically

### For HR Managers

#### View Attendance Details
1. Go to `Attendances > Attendances`
2. Open any attendance record
3. View the "Location Information" section for check-in and check-out details

#### View on Maps
- Click the "View on Maps" button next to GPS coordinates
- Opens Google Maps with the exact location

### Privacy & Permissions

- Device tracking can be enabled/disabled company-wide
- No tracking occurs for manual attendance entries
- Location data is only collected when explicitly enabled
- GPS coordinates are only captured when the browser/device supports geolocation

## Technical Details

### Database Fields

**Check-in Fields:**
- `in_latitude`: GPS latitude
- `in_longitude`: GPS longitude  
- `in_location`: Location name
- `in_ip_address`: IP address
- `in_browser`: Browser information
- `in_mode`: Check-in mode

**Check-out Fields:**
- `out_latitude`: GPS latitude
- `out_longitude`: GPS longitude
- `out_location`: Location name  
- `out_ip_address`: IP address
- `out_browser`: Browser information
- `out_mode`: Check-out mode

### Dependencies

- `hr_attendance`: Base attendance module
- `base_geolocalize`: Geocoding services for location resolution

### API Integration

The module extends the following controllers:
- `/hr_attendance/systray_check_in_out`: Systray attendance with geo tracking
- `/hr_attendance/manual_selection`: Kiosk mode with GPS support
- `/hr_attendance/attendance_barcode_scanned`: Barcode scanning with location

## Compatibility

- **Odoo Version**: 18.0
- **Python**: 3.10+
- **Browsers**: Modern browsers with Geolocation API support

## Security & Privacy

- All location data is stored securely in the Odoo database
- Access is controlled by standard HR attendance permissions
- Employees can see when tracking is enabled
- GPS tracking requires explicit browser permission from the user

## Support

For issues, questions, or feature requests, please contact your system administrator or module maintainer.

## License

LGPL-3

## Credits

**Contributors:**
- Your Company

**Maintainer:**
- Your Company
