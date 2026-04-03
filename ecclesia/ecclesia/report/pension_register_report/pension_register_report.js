// Copyright (c) 2026, 	kunle Oduntan and contributors
// For license information, please see license.txt
/* eslint-disable */


frappe.query_reports["Pension Register Report"] = {
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
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_end(),
            "reqd": 1
        },
        {
            "fieldname": "period_month",
            "label": __("Period Month"),
            "fieldtype": "Select",
            "options": "\nJanuary\nFebruary\nMarch\nApril\nMay\nJune\nJuly\nAugust\nSeptember\nOctober\nNovember\nDecember"
        },
        {
            "fieldname": "period_year",
            "label": __("Period Year"),
            "fieldtype": "Int",
            "default": new Date().getFullYear()
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department"
        },
        {
            "fieldname": "pension_fund_administrator",
            "label": __("Pension Fund Administrator"),
            "fieldtype": "Link",
            "options": "Supplier",
            "get_query": function() {
                return {
                    filters: {
                        "custom_is_pension_fund_administrator": 1
                    }
                };
            }
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": "\nDraft\nSubmitted\nPaid\nRemitted\nCancelled"
        },
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee"
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname === "status" && data) {
            let color = {
                'Draft': 'grey',
                'Submitted': 'blue',
                'Paid': 'green',
                'Remitted': 'green',
                'Cancelled': 'red'
            }[data.status] || 'grey';
            
            value = `<span class="indicator ${color}">${data.status}</span>`;
        }
        
        // Highlight large contributions
        if (column.fieldname === "total_contribution" && data) {
            if (parseFloat(data.total_contribution) > 500000) {
                value = `<span style="color: #e74c3c; font-weight: bold;">${value}</span>`;
            }
        }
        
        return value;
    },
    
    "onload": function(report) {
        // Add custom button for Excel export with styling
        report.page.add_inner_button(__("Export to Excel"), function() {
            export_to_excel_with_style(report);
        }, __("📊 Tools"));
        
        // Add button to create remittance schedule
        report.page.add_inner_button(__("Create Remittance Schedule"), function() {
            create_remittance_from_report(report);
        }, __("📊 Tools"));
        
        // Add button for PFA summary
        report.page.add_inner_button(__("PFA Summary"), function() {
            show_pfa_summary(report);
        }, __("📊 Tools"));
    }
};

function export_to_excel_with_style(report) {
    // Get report data
    let data = report.data;
    let columns = report.columns;
    let filters = report.get_filter_values();
    
    if (!data || data.length === 0) {
        frappe.msgprint(__("No data to export"));
        return;
    }
    
    // Prepare Excel data
    let excel_data = [];
    
    // Title rows
    excel_data.push(["PENSION REGISTER REPORT"]);
    excel_data.push([]);
    excel_data.push(["Company:", filters.company]);
    excel_data.push(["Period:", `${filters.from_date} to ${filters.to_date}`]);
    excel_data.push(["Generated:", frappe.datetime.now_datetime()]);
    excel_data.push([]);
    
    // Headers
    let headers = columns.map(col => col.label);
    excel_data.push(headers);
    
    // Data rows
    data.forEach(row => {
        let rowData = columns.map(col => {
            let value = row[col.fieldname];
            
            // Format currency
            if (col.fieldtype === "Currency" && value) {
                return parseFloat(value).toFixed(2);
            }
            
            return value || "";
        });
        excel_data.push(rowData);
    });
    
    // Summary rows
    excel_data.push([]);
    excel_data.push(["SUMMARY"]);
    
    let total_employees = data.length;
    let total_employee = data.reduce((sum, row) => sum + (parseFloat(row.employee_contribution) || 0), 0);
    let total_employer = data.reduce((sum, row) => sum + (parseFloat(row.employer_contribution) || 0), 0);
    let total_voluntary = data.reduce((sum, row) => sum + (parseFloat(row.voluntary_contribution) || 0), 0);
    let grand_total = total_employee + total_employer + total_voluntary;
    
    excel_data.push(["Total Employees:", total_employees]);
    excel_data.push(["Employee Contribution:", total_employee.toFixed(2)]);
    excel_data.push(["Employer Contribution:", total_employer.toFixed(2)]);
    excel_data.push(["Voluntary Contribution:", total_voluntary.toFixed(2)]);
    excel_data.push(["GRAND TOTAL:", grand_total.toFixed(2)]);
    
    // Convert to CSV
    let csv = excel_data.map(row =>
        row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(",")
    ).join("\n");
    
    // Download
    let filename = `Pension_Register_${filters.company}_${frappe.datetime.now_date()}.csv`;
    frappe.tools.downloadify(csv, null, filename);
    
    frappe.show_alert({
        message: __("Excel file downloaded successfully"),
        indicator: "green"
    }, 5);
}

function create_remittance_from_report(report) {
    let filters = report.get_filter_values();
    
    if (!filters.company || !filters.period_month || !filters.period_year) {
        frappe.msgprint(__("Please select Company, Period Month and Period Year"));
        return;
    }
    
    frappe.new_doc("Pension Remittance Schedule", {
        "company": filters.company,
        "period_month": filters.period_month,
        "period_year": filters.period_year
    });
}

function show_pfa_summary(report) {
    let data = report.data;
    
    if (!data || data.length === 0) {
        frappe.msgprint(__("No data available"));
        return;
    }
    
    // Group by PFA
    let pfa_summary = {};
    data.forEach(row => {
        let pfa = row.pfa || "Unknown";
        if (!pfa_summary[pfa]) {
            pfa_summary[pfa] = {
                employees: 0,
                employee_contrib: 0,
                employer_contrib: 0,
                voluntary: 0,
                total: 0
            };
        }
        
        pfa_summary[pfa].employees += 1;
        pfa_summary[pfa].employee_contrib += parseFloat(row.employee_contribution || 0);
        pfa_summary[pfa].employer_contrib += parseFloat(row.employer_contribution || 0);
        pfa_summary[pfa].voluntary += parseFloat(row.voluntary_contribution || 0);
        pfa_summary[pfa].total += parseFloat(row.total_contribution || 0);
    });
    
    // Build HTML table
    let html = `
        <div style="padding: 20px;">
            <h4>PFA-wise Summary</h4>
            <table class="table table-bordered">
                <thead style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                    <tr>
                        <th>PFA</th>
                        <th class="text-right">Employees</th>
                        <th class="text-right">Employee Contrib</th>
                        <th class="text-right">Employer Contrib</th>
                        <th class="text-right">Voluntary</th>
                        <th class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    for (let pfa in pfa_summary) {
        let summary = pfa_summary[pfa];
        html += `
            <tr>
                <td><strong>${pfa}</strong></td>
                <td class="text-right">${summary.employees}</td>
                <td class="text-right">${frappe.format(summary.employee_contrib, {fieldtype: 'Currency'})}</td>
                <td class="text-right">${frappe.format(summary.employer_contrib, {fieldtype: 'Currency'})}</td>
                <td class="text-right">${frappe.format(summary.voluntary, {fieldtype: 'Currency'})}</td>
                <td class="text-right"><strong>${frappe.format(summary.total, {fieldtype: 'Currency'})}</strong></td>
            </tr>
        `;
    }
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    frappe.msgprint({
        title: __("PFA Summary"),
        message: html,
        wide: true
    });
}