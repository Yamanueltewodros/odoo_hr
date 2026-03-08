/** @odoo-module */
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
// Action manager for printing xlsx report
registry.category("ir.actions.report handlers").add("xlsx", async (action) => {
    if (action.report_type === 'xlsx') {
        await download({
            url: '/xlsx_reports',
            data: action.data,
        });
    }
});
