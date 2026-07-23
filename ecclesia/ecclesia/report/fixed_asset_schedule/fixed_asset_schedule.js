// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt


frappe.query_reports["Fixed Asset Schedule"] = {
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
            "fieldname": "asset_category",
            "label": __("Asset Category"),
            "fieldtype": "Link",
            "options": "Fixed Asset Category"
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department"
        },
        {
            "fieldname": "cost_center",
            "label": __("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center"
        },
        {
            "fieldname": "asset_status",
            "label": __("Asset Status"),
            "fieldtype": "Select",
            "options": ["All", "Active", "Under Maintenance", "Disposed", "Fully Depreciated", "Scrapped", "Transferred", "Draft"],
            "default": "All"
        },
        {
            "fieldname": "from_date",
            "label": __("Purchase From Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": __("Purchase To Date"),
            "fieldtype": "Date"
        },
        {
            "fieldname": "is_depreciable",
            "label": __("Depreciable Assets Only"),
            "fieldtype": "Check"
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Color code status
        if (column.fieldname === "asset_status") {
            let colors = {
                "Active": "#28a745",
                "Draft": "#6c757d",
                "Under Maintenance": "#ffc107",
                "Disposed": "#dc3545",
                "Fully Depreciated": "#17a2b8",
                "Scrapped": "#6c757d",
                "Transferred": "#fd7e14"
            };
            
            let color = colors[value] || "#6c757d";
            value = `<span style="background-color: ${color}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">${value}</span>`;
        }
        
        // Color code values
        if (column.fieldname === "current_net_book_value") {
            if (data.current_net_book_value === 0) {
                value = `<span style="color: #6c757d;">${value}</span>`;
            } else if (data.current_net_book_value < 0) {
                value = `<span style="color: #dc3545;">${value}</span>`;
            }
        }
        
        // Highlight fully depreciated assets
        if (column.fieldname === "depreciation_percentage_complete") {
            let percentage = parseFloat(value);
            if (percentage >= 100) {
                value = `<span style="color: #17a2b8; font-weight: bold;">${value}</span>`;
            } else if (percentage >= 75) {
                value = `<span style="color: #fd7e14;">${value}</span>`;
            }
        }
        
        return value;
    },
    "onload": function(report) {
        // Add download button
        report.page.add_inner_button(__("Download Excel"), function() {
            download_excel(report);
        });
        
        // Add refresh button
        report.page.add_inner_button(__("Refresh"), function() {
            report.refresh();
        });
    }
};

function download_excel(report) {
    // Get current filters
    let filters = report.filters;
    let filters_dict = {};
    
    filters.forEach(filter => {
        if (filter.value && filter.value !== "All") {
            filters_dict[filter.fieldname] = filter.value;
        }
    });
    
    frappe.call({
        method: "ecclesia.ecclesia.report.fixed_asset_schedule.fixed_asset_schedule.download_excel",
        args: {
            filters: filters_dict
        },
        callback: function(response) {
            if (response.message) {
                // Create download link
                const link = document.createElement("a");
                link.href = "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64," + response.message;
                const date = new Date().toISOString().slice(0, 10);
                link.download = `Fixed_Asset_Schedule_${date}.xlsx`;
                link.click();
            }
        }
    });
}