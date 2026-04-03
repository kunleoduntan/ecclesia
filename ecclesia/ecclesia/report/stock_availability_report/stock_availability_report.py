# Copyright (c) 2026, 	kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe import _
from frappe.utils import flt, fmt_money, getdate, today


def execute(filters=None):
    """
    Main execution function for Stock Availability Report
    Returns columns and data for the report
    """
    if not filters:
        filters = {}
    
    # Validate filters
    validate_filters(filters)
    
    # Get columns based on criterion
    columns = get_columns(filters)
    
    # Get data
    data = get_data(filters)
    
    # Get chart data
    chart = get_chart_data(data, filters)
    
    # Get report summary
    report_summary = get_report_summary(data, filters)
    
    return columns, data, None, chart, report_summary


def validate_filters(filters):
    """Validate required filters"""
    if not filters.get("company"):
        frappe.throw(_("Company is mandatory"))
    
    if not filters.get("warehouse"):
        frappe.throw(_("Warehouse is mandatory"))
    
    if not filters.get("report_date"):
        filters["report_date"] = today()
    
    # Ensure report date is not in future
    if getdate(filters.get("report_date")) > getdate(today()):
        frappe.throw(_("Report Date cannot be in the future"))
    
    if not filters.get("criterion"):
        filters["criterion"] = "Availability"


def get_columns(filters):
    """Define columns based on criterion"""
    criterion = filters.get("criterion", "Availability")
    
    # Get currency
    currency = frappe.db.get_value('Company', filters.get('company'), 'default_currency') or "NGN"
    
    columns = [
        {
            "fieldname": "item_code",
            "label": _("Item Code"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 140
        },
        {
            "fieldname": "item_name",
            "label": _("Item Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "item_group",
            "label": _("Item Group"),
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 140
        },
        {
            "fieldname": "uom",
            "label": _("UOM"),
            "fieldtype": "Link",
            "options": "UOM",
            "width": 80
        }
    ]
    
    if criterion == "Availability":
        columns.extend([
            {
                "fieldname": "qty",
                "label": _("Quantity"),
                "fieldtype": "Float",
                "width": 100,
                "precision": 2
            },
            {
                "fieldname": "reorder_level",
                "label": _("Reorder Level"),
                "fieldtype": "Float",
                "width": 120,
                "precision": 2
            },
            {
                "fieldname": "safety_stock",
                "label": _("Safety Stock"),
                "fieldtype": "Float",
                "width": 110,
                "precision": 2
            },
            {
                "fieldname": "minimum_order_qty",
                "label": _("Min Order Qty"),
                "fieldtype": "Float",
                "width": 120,
                "precision": 2
            },
            {
                "fieldname": "cost_price",
                "label": _(f"Cost Price ({currency})"),
                "fieldtype": "Currency",
                "options": "currency",
                "width": 130
            },
            {
                "fieldname": "amount",
                "label": _(f"Amount ({currency})"),
                "fieldtype": "Currency",
                "options": "currency",
                "width": 140
            },
            {
                "fieldname": "stock_status",
                "label": _("Status"),
                "fieldtype": "Data",
                "width": 120
            }
        ])
    else:  # Reorder Level
        columns.extend([
            {
                "fieldname": "qty",
                "label": _("Current Qty"),
                "fieldtype": "Float",
                "width": 110,
                "precision": 2
            },
            {
                "fieldname": "reorder_level",
                "label": _("Reorder Level"),
                "fieldtype": "Float",
                "width": 120,
                "precision": 2
            },
            {
                "fieldname": "safety_stock",
                "label": _("Safety Stock"),
                "fieldtype": "Float",
                "width": 110,
                "precision": 2
            },
            {
                "fieldname": "reorder_qty",
                "label": _("Reorder Qty"),
                "fieldtype": "Float",
                "width": 110,
                "precision": 2
            },
            {
                "fieldname": "minimum_order_qty",
                "label": _("Min Order Qty"),
                "fieldtype": "Float",
                "width": 120,
                "precision": 2
            },
            {
                "fieldname": "cost_price",
                "label": _(f"Cost Price ({currency})"),
                "fieldtype": "Currency",
                "options": "currency",
                "width": 130
            },
            {
                "fieldname": "reorder_amount",
                "label": _(f"Reorder Amount ({currency})"),
                "fieldtype": "Currency",
                "options": "currency",
                "width": 150
            },
            {
                "fieldname": "urgency",
                "label": _("Urgency"),
                "fieldtype": "Data",
                "width": 100
            }
        ])
    
    # Add currency field
    columns.append({
        "fieldname": "currency",
        "label": _("Currency"),
        "fieldtype": "Link",
        "options": "Currency",
        "hidden": 1
    })
    
    return columns


def get_data(filters):
    """Fetch stock data based on filters"""
    company = filters.get("company")
    warehouse = filters.get("warehouse")
    report_date = filters.get("report_date")
    criterion = filters.get("criterion", "Availability")
    item_group = filters.get("item_group")
    
    # Get currency
    currency = frappe.db.get_value('Company', company, 'default_currency') or "NGN"
    
    # Build the query
    conditions = ""
    if item_group:
        conditions += " AND i.item_group = %(item_group)s"
    
    query = f"""
        SELECT 
            sle.item_code,
            sle.warehouse,
            sle.stock_uom as uom,
            sle.posting_date,
            sle.qty_after_transaction as qty,
            COALESCE(sle.valuation_rate, sle.outgoing_rate, sle.incoming_rate, 0) as cost_price,
            i.item_name,
            i.item_group,
            i.safety_stock,
            sle.creation
        FROM (
            SELECT 
                item_code,
                warehouse,
                MAX(creation) as max_creation
            FROM `tabStock Ledger Entry`
            WHERE 
                company = %(company)s
                AND warehouse = %(warehouse)s
                AND docstatus = 1
                AND posting_date <= %(report_date)s
            GROUP BY item_code, warehouse
        ) latest
        INNER JOIN `tabStock Ledger Entry` sle 
            ON sle.item_code = latest.item_code 
            AND sle.warehouse = latest.warehouse
            AND sle.creation = latest.max_creation
        LEFT JOIN `tabItem` i ON i.name = sle.item_code
        WHERE sle.qty_after_transaction != 0
            {conditions}
        ORDER BY sle.item_code
    """
    
    stock_entries = frappe.db.sql(query, {
        'company': company,
        'warehouse': warehouse,
        'report_date': report_date,
        'item_group': item_group
    }, as_dict=1)
    
    if not stock_entries:
        return []
    
    # Get reorder data from Item Reorder table
    item_codes = [d.item_code for d in stock_entries]
    reorder_data = get_item_reorder_data(item_codes, warehouse)
    
    # Process data
    data = []
    for entry in stock_entries:
        item_code = entry.get('item_code')
        qty = flt(entry.get('qty', 0))
        cost_price = flt(entry.get('cost_price', 0))
        
        # Get reorder info
        reorder_info = reorder_data.get(item_code, {})
        reorder_level = flt(reorder_info.get('reorder_level', 0))
        safety_stock = flt(entry.get('safety_stock', 0))
        minimum_order_qty = flt(reorder_info.get('minimum_order_qty', 0))
        
        # Calculate reorder qty
        reorder_qty = max(0, reorder_level - qty)
        
        # Apply criterion filter
        if criterion == "Reorder Level" and qty >= reorder_level:
            continue
        
        # Determine stock status
        if qty <= safety_stock and safety_stock > 0:
            stock_status = "Critical"
            urgency = "High"
        elif qty < reorder_level:
            stock_status = "Below Reorder"
            urgency = "Medium"
        else:
            stock_status = "Adequate"
            urgency = "Low"
        
        row = {
            'item_code': item_code,
            'item_name': entry.get('item_name'),
            'item_group': entry.get('item_group'),
            'uom': entry.get('uom'),
            'qty': qty,
            'reorder_level': reorder_level,
            'safety_stock': safety_stock,
            'minimum_order_qty': minimum_order_qty,
            'cost_price': cost_price,
            'currency': currency,
            'stock_status': stock_status,
            'urgency': urgency
        }
        
        if criterion == "Availability":
            row['amount'] = qty * cost_price
        else:
            row['reorder_qty'] = reorder_qty
            row['reorder_amount'] = reorder_qty * cost_price
        
        data.append(row)
    
    return data


def get_item_reorder_data(item_codes, warehouse):
    """Get reorder level and minimum order qty from Item Reorder table"""
    if not item_codes:
        return {}
    
    reorder_data = {}
    
    # Get from Item Reorder table
    item_reorder = frappe.db.sql("""
        SELECT 
            parent as item_code,
            warehouse_reorder_level as reorder_level,
            warehouse_reorder_qty as minimum_order_qty
        FROM `tabItem Reorder`
        WHERE parent IN %(items)s
            AND warehouse = %(warehouse)s
    """, {'items': item_codes, 'warehouse': warehouse}, as_dict=1)
    
    for row in item_reorder:
        reorder_data[row.item_code] = {
            'reorder_level': flt(row.reorder_level),
            'minimum_order_qty': flt(row.minimum_order_qty)
        }
    
    # Get from Item master for items not in reorder table
    items_data = frappe.db.sql("""
        SELECT 
            name as item_code,
            COALESCE(min_order_qty, 0) as min_order_qty
        FROM `tabItem`
        WHERE name IN %(items)s
    """, {'items': item_codes}, as_dict=1)
    
    for item in items_data:
        if item.item_code not in reorder_data:
            reorder_data[item.item_code] = {
                'reorder_level': 0,
                'minimum_order_qty': flt(item.min_order_qty)
            }
    
    return reorder_data


def get_chart_data(data, filters):
    """Generate chart data for visualization"""
    if not data:
        return None
    
    criterion = filters.get("criterion", "Availability")
    
    if criterion == "Availability":
        # Stock Status Distribution
        status_count = {}
        for row in data:
            status = row.get('stock_status', 'Unknown')
            status_count[status] = status_count.get(status, 0) + 1
        
        chart = {
            "data": {
                "labels": list(status_count.keys()),
                "datasets": [
                    {
                        "name": "Items",
                        "values": list(status_count.values())
                    }
                ]
            },
            "type": "donut",
            "colors": ["#10B981", "#F59E0B", "#EF4444"],
            "height": 280,
            "title": "Stock Status Distribution"
        }
    else:
        # Reorder Urgency Distribution
        urgency_count = {}
        for row in data:
            urgency = row.get('urgency', 'Unknown')
            urgency_count[urgency] = urgency_count.get(urgency, 0) + 1
        
        chart = {
            "data": {
                "labels": list(urgency_count.keys()),
                "datasets": [
                    {
                        "name": "Items",
                        "values": list(urgency_count.values())
                    }
                ]
            },
            "type": "bar",
            "colors": ["#EF4444", "#F59E0B", "#10B981"],
            "height": 280,
            "title": "Reorder Urgency Level"
        }
    
    return chart


def get_report_summary(data, filters):
    """Generate summary cards for the report"""
    if not data:
        return []
    
    criterion = filters.get("criterion", "Availability")
    currency = frappe.db.get_value('Company', filters.get('company'), 'default_currency') or "NGN"
    
    summary = []
    
    # Total Items
    summary.append({
        "value": len(data),
        "label": _("Total Items"),
        "datatype": "Int",
        "indicator": "blue"
    })
    
    if criterion == "Availability":
        # Total Stock Value
        total_value = sum(flt(row.get('amount', 0)) for row in data)
        summary.append({
            "value": total_value,
            "label": _(f"Total Stock Value ({currency})"),
            "datatype": "Currency",
            "indicator": "green"
        })
        
        # Items Below Reorder
        below_reorder = len([d for d in data if d.get('stock_status') in ['Below Reorder', 'Critical']])
        summary.append({
            "value": below_reorder,
            "label": _("Items Below Reorder"),
            "datatype": "Int",
            "indicator": "orange" if below_reorder > 0 else "green"
        })
        
        # Critical Items
        critical = len([d for d in data if d.get('stock_status') == 'Critical'])
        if critical > 0:
            summary.append({
                "value": critical,
                "label": _("Critical Items (≤ Safety Stock)"),
                "datatype": "Int",
                "indicator": "red"
            })
    else:
        # Total Reorder Cost
        total_reorder_cost = sum(flt(row.get('reorder_amount', 0)) for row in data)
        summary.append({
            "value": total_reorder_cost,
            "label": _(f"Total Reorder Cost ({currency})"),
            "datatype": "Currency",
            "indicator": "orange"
        })
        
        # High Urgency Items
        high_urgency = len([d for d in data if d.get('urgency') == 'High'])
        if high_urgency > 0:
            summary.append({
                "value": high_urgency,
                "label": _("High Urgency Items"),
                "datatype": "Int",
                "indicator": "red"
            })
        
        # Average Reorder Quantity
        avg_reorder = sum(flt(row.get('reorder_qty', 0)) for row in data) / len(data) if data else 0
        summary.append({
            "value": avg_reorder,
            "label": _("Avg Reorder Qty"),
            "datatype": "Float",
            "indicator": "blue"
        })
    
    return summary