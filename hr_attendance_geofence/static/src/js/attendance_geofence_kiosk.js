/** @odoo-module **/

/**
 * attendance_geofence_kiosk.js
 *
 * Patches kioskAttendanceApp.onBarcodeScanned() to send GPS coordinates.
 *
 * WHY: The standard onBarcodeScanned() calls plain rpc() — no GPS is sent.
 * manual_selection already uses makeRpcWithGeolocation() so GPS is sent there.
 * We only need to patch onBarcodeScanned() to use makeRpcWithGeolocation() too,
 * so the server geofence controller can validate barcode check-ins.
 *
 * We also handle the geofence_error key returned by the server.
 */

import { patch } from '@web/core/utils/patch';
import KioskModule from '@hr_attendance/public_kiosk/public_kiosk_app';

const kioskAttendanceApp = KioskModule.kioskAttendanceApp;

patch(kioskAttendanceApp.prototype, {

    async onBarcodeScanned(barcode) {
        if (this.lockScanner || this.state.active_display !== 'main') {
            return;
        }
        this.lockScanner = true;
        this.ui.block();

        try {
            // Use makeRpcWithGeolocation instead of plain rpc
            // so latitude/longitude are sent to the server for geofence check
            const result = await this.makeRpcWithGeolocation(
                'attendance_barcode_scanned',
                { barcode, token: this.props.token }
            );

            if (result && result.geofence_error) {
                // Blocked by server-side geofence
                this.displayNotification(result.geofence_error);
            } else if (result && result.employee_name) {
                this.employeeData = result;
                this.switchDisplay('greet');
            } else {
                this.displayNotification(
                    `No employee corresponding to Badge ID '${barcode}.'`
                );
            }
        } catch (error) {
            this.displayNotification(error?.data?.message || error.message);
        } finally {
            this.lockScanner = false;
            this.ui.unblock();
        }
    },

    // Also handle geofence_error for manual selection responses
    async onManualSelection(employeeId, enteredPin) {
        const result = await this.makeRpcWithGeolocation('manual_selection', {
            token: this.props.token,
            employee_id: employeeId,
            pin_code: enteredPin,
        });

        if (result && result.geofence_error) {
            this.displayNotification(result.geofence_error);
        } else if (result && result.attendance) {
            this.employeeData = result;
            this.switchDisplay('greet');
        } else {
            if (enteredPin) {
                this.displayNotification('Wrong Pin');
            }
        }
    },
});
