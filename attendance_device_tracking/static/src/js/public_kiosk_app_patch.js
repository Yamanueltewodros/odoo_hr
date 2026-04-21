import { kioskAttendanceApp } from "@hr_attendance/public_kiosk/public_kiosk_app";
import { isIosApp } from "@web/core/browser/feature_detection";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(kioskAttendanceApp.prototype, {
    async makeRpcWithGeolocation(route, params) {
        if (!this.props.deviceTrackingEnabled || !navigator.geolocation || isIosApp()) {
            return rpc(route, { ...params });
        }

        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude, longitude } }) => {
                    const result = await rpc(route, {
                        ...params,
                        latitude,
                        longitude,
                    });
                    resolve(result);
                },
                async () => {
                    const result = await rpc(route, { ...params });
                    resolve(result);
                },
                { enableHighAccuracy: true }
            );
        });
    },
});
