# Upgrade Guide to Odoo 18

This guide helps you upgrade the Attendance Device Tracking module to Odoo 18.

## Breaking Changes

### 1. SQL Query Updates
**Before (Odoo 17 and earlier):**
```python
from odoo.tools import SQL

request.env.cr.execute(
    SQL(
        "SELECT COUNT(password) FROM res_users WHERE id=%(user_id)s",
        user_id=request.env.user.id,
    )
)
```

**After (Odoo 18):**
```python
request.env.cr.execute(
    "SELECT COUNT(password) FROM res_users WHERE id = %s",
    (request.env.user.id,),
)
```

The `SQL` wrapper has been removed. Use standard parameterized queries.

### 2. Base URL Retrieval
**Before:**
```python
self.env["res.company"].get_base_url()
```

**After:**
```python
self.env["ir.config_parameter"].sudo().get_param("web.base.url")
```

Use the config parameter method for better compatibility.

### 3. String Formatting
**Before:**
```python
url = "/hr_attendance/%s" % company.attendance_kiosk_key
location = "https://maps.google.com?q=%s,%s" % (latitude, longitude)
```

**After:**
```python
url = f"/hr_attendance/{company.attendance_kiosk_key}"
location = f"https://maps.google.com?q={latitude},{longitude}"
```

Use f-strings for better readability and performance.

### 4. View References
The module assumes standard Odoo 18 hr_attendance views. If you've customized views, ensure XPath expressions are compatible:

```xml
<!-- Make sure these elements exist in your base views -->
<xpath expr="//field[@name='check_out']" position="after">
<xpath expr="//group[@name='check_in_group']" position="inside">
```

## Upgrade Steps

### Step 1: Backup
```bash
# Backup your database
pg_dump your_database > backup_before_upgrade.sql

# Backup your custom modules
cp -r /path/to/addons/attendance_device_tracking /path/to/backup/
```

### Step 2: Install Updated Module
```bash
# Remove old version
rm -rf /path/to/addons/attendance_device_tracking

# Copy new version
cp -r attendance_device_tracking /path/to/addons/

# Restart Odoo
sudo systemctl restart odoo
```

### Step 3: Update Module
```bash
# Via command line
odoo-bin -u attendance_device_tracking -d your_database

# Or via UI
# Settings > Apps > Attendance Device Tracking > Upgrade
```

### Step 4: Verify Installation
1. Check that all attendance records still have their location data
2. Test check-in/out from systray
3. Test kiosk mode with GPS tracking
4. Verify Google Maps links work correctly
5. Check that settings page shows device tracking option

## Data Migration

### No Data Loss
All existing attendance records with location data will be preserved. The upgrade only affects:
- Code structure
- Field definitions (metadata only)
- View layouts

### Field Mapping
All fields remain the same:
- `in_latitude`, `in_longitude`, `in_location`
- `in_ip_address`, `in_browser`, `in_mode`
- `out_latitude`, `out_longitude`, `out_location`
- `out_ip_address`, `out_browser`, `out_mode`

## Testing Checklist

After upgrade, verify:
- [ ] Systray check-in/out works
- [ ] GPS location is captured (when enabled)
- [ ] IP address is recorded
- [ ] Browser information is captured
- [ ] Kiosk mode functions properly
- [ ] Google Maps links open correctly
- [ ] Settings page accessible
- [ ] Existing attendance records display correctly
- [ ] Location fields visible in tree and form views

## Rollback Procedure

If you need to rollback:

```bash
# Restore database
psql your_database < backup_before_upgrade.sql

# Restore old module version
rm -rf /path/to/addons/attendance_device_tracking
cp -r /path/to/backup/attendance_device_tracking /path/to/addons/

# Restart Odoo
sudo systemctl restart odoo
```

## Common Issues

### Issue: "View not found" error
**Solution:** Update hr_attendance to latest Odoo 18 version first

### Issue: GPS not capturing
**Solution:** 
- Ensure HTTPS is enabled (required for browser geolocation API)
- Check browser permissions for location access
- Verify "Device & Location Tracking" is enabled in settings

### Issue: Import errors
**Solution:**
- Check Python version (requires 3.10+)
- Ensure all dependencies are installed
- Verify base_geolocalize module is installed

## Support

For issues during upgrade:
1. Check the CHANGELOG.md for detailed changes
2. Review error logs: `/var/log/odoo/odoo.log`
3. Contact your system administrator
4. Refer to Odoo 18 migration guide

## Performance Notes

The Odoo 18 version includes:
- Optimized database queries
- Better caching for geocoding results
- Reduced JavaScript bundle size
- Improved error handling

No performance degradation expected from the upgrade.
