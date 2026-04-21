# Changelog

## [18.0.1.0.0] - 2026-04-21

### Added
- Initial release for Odoo 18.0
- Complete device and location tracking for attendance
- GPS coordinates capture for check-in/out
- IP address and browser detection
- Google Maps integration
- Support for Kiosk and Systray modes
- Comprehensive README documentation
- Security access rules

### Changed
- Updated for Odoo 18.0 compatibility
- Improved code structure and documentation
- Enhanced error handling in controllers
- Better field labels and help texts
- Modern f-string formatting in Python code
- Improved XML view structure
- Better JavaScript compatibility

### Fixed
- Fixed SQL query in has_password() method (removed SQL wrapper)
- Fixed base URL retrieval in res_company (use ir.config_parameter)
- Added null checks for geoip and user_agent objects
- Improved error handling for missing GPS coordinates
- Fixed view XPath expressions for Odoo 18 compatibility
- Added missing field invisible attributes
- Improved button visibility logic

### Technical Details
- Python 3.10+ compatible
- Uses modern Odoo 18 ORM patterns
- Proper use of f-strings instead of % formatting
- Enhanced docstrings and comments
- Better separation of concerns in controllers
- Proper NULL handling in database queries

### Dependencies
- hr_attendance (Odoo core module)
- base_geolocalize (Odoo core module)

### Security
- Proper access control lists (ACL)
- Privacy-aware location tracking
- User permission-based GPS access
