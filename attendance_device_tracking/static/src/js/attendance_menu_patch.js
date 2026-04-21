import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ConnectionLostError, rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { isIosApp } from "@web/core/browser/feature_detection";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, {
    async checking(latitude = false, longitude = false) {
        try {
            this.employee = await rpc("/hr_attendance/systray_check_in_out", {
                latitude,
                longitude,
            });
            this._searchReadEmployeeFill();
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.notification.add(_t("Connection lost. Check in/out could not be recorded."), {
                    title: _t("Attendance Error"),
                    type: "danger",
                    sticky: false,
                });
            } else {
                throw error;
            }
        } finally {
            this._attendanceInProgress = false;
        }
    },

    confirmChecking() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Unable to get a valid location. Do you want to proceed with your check-in/out anyway?"),
            confirmLabel: _t("Proceed Anyway"),
            confirm: async () => await this.checking(),
            cancel: () => this._attendanceInProgress = false,
        });
    },

    async signInOut() {
        this.dropdown.close();
        if (this._attendanceInProgress) {
            return;
        }
        this._attendanceInProgress = true;

        const trackingEnabled = this.employee && this.employee.device_tracking_enabled;
        if (trackingEnabled && !isIosApp() && navigator.geolocation && navigator.onLine) {
            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude, longitude } }) => {
                    await this.checking(latitude, longitude);
                },
                () => {
                    this.confirmChecking();
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                }
            );
        } else if (trackingEnabled) {
            this.confirmChecking();
        } else {
            await this.checking();
        }
    },
});
