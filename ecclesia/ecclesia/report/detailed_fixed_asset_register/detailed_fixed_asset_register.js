// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt


frappe.query_reports["Detailed Fixed Asset Register"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "fiscal_year",
            "label": __("Fiscal Year"),
            "fieldtype": "Select",
            "options": get_fiscal_year_options(),
            "default": new Date().getFullYear().toString(),
            "reqd": 1
        },
        {
            "fieldname": "asset_category",
            "label": __("Asset Category"),
            "fieldtype": "Link",
            "options": "Fixed Asset Category"
        },
        {
            "fieldname": "asset_status",
            "label": __("Asset Status"),
            "fieldtype": "Select",
            "options": "\nSubmitted\nDraft\nDisposed\nScrapped\nIn Maintenance"
        }
    ],
    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (data && data.is_total_row) {
            value = `<span style="font-weight: bold; color: #1a5276;">${value}</span>`;
        }

        if (data && (column.fieldname === "revaluations" || column.fieldname === "depreciation_revaluations")) {
            if (data[column.fieldname] > 0) {
                value = `<span style="color: #0066cc; font-weight: bold;">${value}</span>`;
            } else if (data[column.fieldname] < 0) {
                value = `<span style="color: #cc0000; font-weight: bold;">${value}</span>`;
            }
        }

        return value;
    },
    "onload": function (report) {
        report.page.add_inner_button(__("Download Excel"), function () {
            download_excel(report);
        });

        report.page.add_inner_button(__("Refresh"), function () {
            report.refresh();
        });
    }
};

function get_fiscal_year_options() {
    let current_year = new Date().getFullYear();
    let options = [];
    for (let year = current_year; year >= current_year - 10; year--) {
        options.push(year.toString());
    }
    return options;
}

function download_excel(report) {
    let filters = report.filters;
    let filters_dict = {};

    filters.forEach(filter => {
        if (filter.value) {
            filters_dict[filter.fieldname] = filter.value;
        }
    });

    frappe.call({
        method: "ecclesia.ecclesia.report.detailed_fixed_asset_register.detailed_fixed_asset_register.download_excel",
        args: {
            filters: filters_dict
        },
        callback: function (response) {
            if (response.message) {
                const link = document.createElement("a");
                link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + response.message;
                const date = new Date().toISOString().slice(0, 10);
                link.download = `Fixed_Asset_Register_${date}.xlsx`;
                link.click();
            }
        }
    });
}