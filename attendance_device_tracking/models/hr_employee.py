from odoo import _, exceptions, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _attendance_action_change(self, geo_information=None):
        """
        Override to support geo-tracking information during check-in/out.
        
        :param geo_information: Dictionary containing location data (latitude, longitude, 
                                location, ip_address, browser, mode)
        :return: Created or updated attendance record
        """
        self.ensure_one()
        action_date = fields.Datetime.now()
        
        # Check-in case
        if self.attendance_state != "checked_in":
            vals = {
                "employee_id": self.id,
                "check_in": action_date,
            }
            if geo_information:
                # Add geo tracking fields with 'in_' prefix
                vals.update({
                    f"in_{key}": geo_information[key]
                    for key in geo_information
                })
            return self.env["hr.attendance"].create(vals)
        
        # Check-out case
        attendance = self.env["hr.attendance"].search([
            ("employee_id", "=", self.id),
            ("check_out", "=", False),
        ], limit=1)
        
        if attendance:
            vals = {"check_out": action_date}
            if geo_information:
                # Add geo tracking fields with 'out_' prefix
                vals.update({
                    f"out_{key}": geo_information[key]
                    for key in geo_information
                })
            attendance.write(vals)
        else:
            raise exceptions.UserError(_(
                "Cannot perform check out on %(empl_name)s, could not find corresponding check in. "
                "Your attendances have probably been modified manually by human resources.",
                empl_name=self.sudo().name,
            ))
        
        return attendance

