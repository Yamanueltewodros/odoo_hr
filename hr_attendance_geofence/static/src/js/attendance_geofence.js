/** @odoo-module **/

/**
 * hr_attendance_geofence/static/src/js/attendance_geofence.js
 *
 * Standalone GeofenceButton component for the My Attendances backend view.
 * Loaded via web.assets_backend only.
 */

import { useService }  from '@web/core/utils/hooks';
import { registry }    from '@web/core/registry';
import { Component, useState, onWillStart } from '@odoo/owl';

// ── Haversine (client-side pre-check) ───────────────────────────────────────

function haversine(lat1, lon1, lat2, lon2) {
    const R = 6_371_000;
    const toRad = (d) => (d * Math.PI) / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
}

// ── GPS helper ───────────────────────────────────────────────────────────────

function getCurrentPosition() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocation is not supported by this browser.'));
            return;
        }
        navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 10_000,
            maximumAge: 0,
        });
    });
}

// ── Shared geofence assertion ────────────────────────────────────────────────

export async function assertWithinGeofence(rpc) {
    const cfg = await rpc('/hr_attendance/geofence/config', {});
    let lat = 0, lng = 0;

    if (cfg && (cfg.enabled || cfg.lat)) {
        const pos = await getCurrentPosition();
        lat = pos.coords.latitude;
        lng = pos.coords.longitude;

        if (cfg.enabled && cfg.lat && cfg.lng) {
            const dist = haversine(lat, lng, cfg.lat, cfg.lng);
            if (dist > cfg.radius) {
                throw new Error(
                    cfg.message ||
                    `You are ${Math.round(dist)} m from the office ` +
                    `(allowed: ${cfg.radius} m). Please check in on-site.`
                );
            }
        }
    }
    return { lat, lng };
}

// ── Standalone GeofenceButton (My Attendances backend widget) ────────────────

export class AttendanceGeofenceButton extends Component {
    static template = 'hr_attendance_geofence.GeofenceButton';

    setup() {
        this.rpc          = useService('rpc');
        this.notification = useService('notification');
        this.state        = useState({ loading: false, config: null });

        onWillStart(async () => {
            this.state.config = await this.rpc('/hr_attendance/geofence/config', {});
        });
    }

    async onToggleAttendance() {
        if (this.state.loading) return;
        this.state.loading = true;

        try {
            let lat = 0, lng = 0;
            try {
                const coords = await assertWithinGeofence(this.rpc);
                lat = coords.lat;
                lng = coords.lng;
            } catch (geoErr) {
                this.notification.add(geoErr.message, { type: 'danger', sticky: true });
                return;
            }

            const result = await this.rpc('/hr_attendance/geofence/toggle', { lat, lng });

            if (result.success) {
                this.notification.add(
                    result.action === 'check_in'
                        ? '✔ Checked in successfully.'
                        : '✔ Checked out successfully.',
                    { type: 'success' }
                );
            } else {
                this.notification.add(result.error || 'Unknown error.', {
                    type: 'danger',
                    sticky: true,
                });
            }
        } finally {
            this.state.loading = false;
        }
    }
}

registry.category('actions').add('attendance_geofence_button', AttendanceGeofenceButton);
