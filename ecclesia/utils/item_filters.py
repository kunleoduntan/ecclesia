import frappe
from frappe import _

# Which flag field must be = 1 for items to appear/be allowed on each doctype
DOCTYPE_ITEM_FLAG_MAP = {
    "Sales Invoice": "is_sales_item",
    "Sales Order": "is_sales_item",
    "Purchase Invoice": "is_purchase_item",
    "Purchase Order": "is_purchase_item",
}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(doctype, txt, searchfield, start, page_len, filters):
    """
    Universal Item link-field query.
    Client script passes filters={"parenttype": <calling doctype>}.
    Only items marked correctly for that transaction type are returned.
    """
    parenttype = filters.get("parenttype") if filters else None
    flag_field = DOCTYPE_ITEM_FLAG_MAP.get(parenttype)

    conditions = ["item.disabled = 0"]
    if flag_field:
        conditions.append(f"item.{flag_field} = 1")
    if filters and filters.get("item_group"):
        conditions.append("item.item_group = %(item_group)s")

    condition_str = " and ".join(conditions)

    return frappe.db.sql(
        f"""
        select item.name, item.item_name, item.item_group, item.stock_uom
        from `tabItem` item
        where item.{searchfield} like %(txt)s
        and {condition_str}
        order by
            case when locate(%(_txt)s, item.name) = 0 then 99999 else locate(%(_txt)s, item.name) end,
            item.idx desc, item.name
        limit %(start)s, %(page_len)s
        """,
        {
            "txt": f"%{txt}%",
            "_txt": txt.replace("%", ""),
            "item_group": filters.get("item_group") if filters else None,
            "start": start,
            "page_len": page_len,
        },
    )


def validate_item_type_on_transaction(doc, method=None):
    """
    Server-side guard — catches items added via API, Data Import,
    bulk edit, or any path that bypasses the client-side query,
    so the sales/purchase flag is enforced no matter how the row got there.
    Hook this into doc_events["validate"] for each relevant doctype.
    """
    flag_field = DOCTYPE_ITEM_FLAG_MAP.get(doc.doctype)
    if not flag_field:
        return

    item_codes = list({row.item_code for row in doc.get("items") if row.item_code})
    if not item_codes:
        return

    flag_map = {
        row.name: row.get(flag_field)
        for row in frappe.get_all(
            "Item", filters={"name": ["in", item_codes]}, fields=["name", flag_field]
        )
    }

    label = "Sales Item" if flag_field == "is_sales_item" else "Purchase Item"

    for row in doc.get("items"):
        if row.item_code and not flag_map.get(row.item_code):
            frappe.throw(
                _("Row #{0}: Item {1} is not marked as a {2} and cannot be used in {3}").format(
                    row.idx, frappe.bold(row.item_code), frappe.bold(label), doc.doctype
                )
            )