// ecclesia/report/cycle_completion_status/cycle_completion_status.js

// Shared Excel download handler — injected into each report's JS
function ecclesia_excel_download(report_name, api_method, frm_report) {
    const filters = frm_report ? frm_report.get_values() : {};
    frappe.show_progress(__("Generating Excel"), 10, 100, __("Building workbook..."));
    frappe.call({
        method: api_method,
        args: { filters: JSON.stringify(filters) },
        timeout: 120,
        callback(r) {
            frappe.hide_progress();
            if (!r.message) { frappe.msgprint(__("No data to export.")); return; }
            const { filename, filecontent } = r.message;
            const link = document.createElement("a");
            link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,"
                        + filecontent;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            frappe.show_alert({ message: __("Excel report downloaded: ") + filename,
                                indicator: "green" });
        },
        error() {
            frappe.hide_progress();
            frappe.msgprint(__("Excel generation failed. Check error log."));
        }
    });
}


frappe.query_reports["Cycle Completion Status"] = {

    filters: [
        { fieldname:"cycle", label:__("Performance Cycle"), fieldtype:"Link", options:"Performance Cycle", reqd:1 },
        { fieldname:"department", label:__("Department"), fieldtype:"Link", options:"Department" }
    ],

    onload(report) {
        report.page.add_inner_button(__("Export to Excel"), () => {
            ecclesia_excel_download(
                "cycle_completion_status",
                "ecclesia.report.cycle_completion_status.cycle_completion_status.download_excel",
                report
            );
        }, __("Export"));
    },

    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        // Traffic light for status/completion columns
        const greenKw  = ["✅", "Done", "Shortlisted", "Passed", "Active", "On Track"];
        const amberKw  = ["⏳", "Pending", "Refer to HR", "At Risk", "Extended"];
        const redKw    = ["🔴", "Failed", "Rejected", "Overdue", "Critical"];
        const strVal   = String(data[column.fieldname] || "");

        if (greenKw.some(k => strVal.includes(k))) {
            return `<span style="color:#059669;font-weight:600">${value}</span>`;
        }
        if (amberKw.some(k => strVal.includes(k))) {
            return `<span style="color:#D97706;font-weight:600">${value}</span>`;
        }
        if (redKw.some(k => strVal.includes(k))) {
            return `<span style="color:#DC2626;font-weight:600">${value}</span>`;
        }

        // Score colouring
        if (column.fieldname && column.fieldname.includes("score")) {
            const n = parseFloat(strVal);
            if (!isNaN(n)) {
                const color = n >= 75 ? "#059669" : n >= 60 ? "#2563EB" : n >= 40 ? "#D97706" : "#DC2626";
                return `<span style="color:${color};font-weight:700">${value}</span>`;
            }
        }
        return value;
    }
};
