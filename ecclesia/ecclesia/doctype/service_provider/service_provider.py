# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Service Provider DocType Controller
Manages admin vendors (security, cleaning, maintenance, ISP, etc.)
Key feature: approved providers can be promoted to ERPNext Supplier with one click.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, getdate


class ServiceProvider(Document):

    # ── Lifecycle hooks ──────────────────────────────────────────────────────

    def before_insert(self):
        self._set_defaults()

    def validate(self):
        self._validate_status_transition()
        self._sync_supplier_link()

    def on_update(self):
        self._update_supplier_status_if_linked()

    # ── Validation helpers ───────────────────────────────────────────────────

    def _set_defaults(self):
        if not self.status:
            self.status = "Active"
        if not self.performance_score:
            self.performance_score = 0.0

    def _validate_status_transition(self):
        """Prevent blacklisting a provider that has active contracts."""
        if self.status == "Blacklisted" and not self.is_new():
            active_contracts = frappe.db.count(
                "Service Contract",
                filters={"service_provider": self.name, "status": "Active"}
            )
            if active_contracts:
                frappe.throw(
                    _("Cannot blacklist {0}: there are {1} active contract(s). "
                      "Terminate contracts first.").format(self.provider_name, active_contracts)
                )

    def _sync_supplier_link(self):
        """If a supplier is linked, keep provider_name in sync with Supplier name."""
        if self.supplier:
            supplier_name = frappe.db.get_value("Supplier", self.supplier, "supplier_name")
            if supplier_name and supplier_name != self.provider_name:
                frappe.msgprint(
                    _("Note: Provider name differs from linked Supplier name ({0}).").format(
                        supplier_name
                    ),
                    indicator="orange",
                )

    def _update_supplier_status_if_linked(self):
        """Reflect blacklist on the linked Supplier record."""
        if self.supplier and self.status == "Blacklisted":
            frappe.db.set_value(
                "Supplier", self.supplier, "disabled", 1, update_modified=False
            )

    # ── Computed fields ──────────────────────────────────────────────────────

    def update_active_contracts(self):
        """Recalculate the active_contracts count field (called by Service Contract hooks)."""
        count = frappe.db.count(
            "Service Contract",
            filters={"service_provider": self.name, "status": "Active"}
        )
        self.db_set("active_contracts", count)

    def recalculate_performance_score(self):
        """
        Simple scoring model (0-10):
        - Averaged from linked Service Contract vendor_score values.
        Call from a scheduler or after each contract update.
        """
        scores = frappe.db.get_all(
            "Service Contract",
            filters={"service_provider": self.name, "docstatus": 1},
            fields=["vendor_score"],
        )
        valid = [s.vendor_score for s in scores if s.vendor_score is not None]
        avg = round(sum(valid) / len(valid), 2) if valid else 0.0
        self.db_set("performance_score", avg)


# ── Whitelisted API methods ──────────────────────────────────────────────────

@frappe.whitelist()
def create_supplier_from_provider(service_provider):
    """
    Promote an approved Service Provider to an ERPNext Supplier.
    Called from the JS 'Create Supplier' button.

    Steps
    ─────
    1. Load the Service Provider doc.
    2. Verify it is Active and not already linked to a Supplier.
    3. Create a new Supplier document reusing provider data.
    4. Write the new Supplier name back to service_provider.supplier.
    5. Return the Supplier name for the JS redirect.
    """
    doc = frappe.get_doc("Service Provider", service_provider)

    if doc.status != "Active":
        frappe.throw(_("Only Active service providers can be converted to Suppliers."))

    if doc.supplier:
        frappe.throw(
            _("This provider is already linked to Supplier {0}.").format(doc.supplier)
        )

    # Map service category → ERPNext supplier_group
    group_map = {
        "Security":             "Services",
        "Cleaning / Janitorial": "Services",
        "Internet / ISP":       "Services",
        "Maintenance":          "Services",
        "Catering":             "Services",
        "Waste Management":     "Services",
        "Generator / Power":    "Services",
        "Air Conditioning":     "Services",
        "Elevator":             "Services",
        "Pest Control":         "Services",
        "Landscaping":          "Services",
        "Courier":              "Logistics",
        "Other":                "All Supplier Groups",
    }
    supplier_group = group_map.get(doc.service_category, "All Supplier Groups")

    supplier = frappe.new_doc("Supplier")
    supplier.supplier_name  = doc.provider_name
    supplier.supplier_group = supplier_group
    supplier.supplier_type  = "Company"
    supplier.country        = "Nigeria"

    # Optional contact info
    if doc.phone:
        supplier.mobile_no = doc.phone
    if doc.email:
        supplier.email_id = doc.email

    supplier.flags.ignore_mandatory = True
    supplier.insert(ignore_permissions=True)

    # Link back
    doc.db_set("supplier", supplier.name)

    frappe.msgprint(
        _("Supplier {0} created and linked to this provider.").format(
            frappe.utils.get_link_to_form("Supplier", supplier.name)
        ),
        indicator="green",
    )

    return supplier.name


@frappe.whitelist()
def get_provider_summary(service_provider):
    """Return KPI summary for the provider dashboard HTML field."""
    contracts = frappe.db.get_all(
        "Service Contract",
        filters={"service_provider": service_provider},
        fields=["status", "contract_value", "days_to_expiry", "vendor_score"],
    )

    active   = [c for c in contracts if c.status == "Active"]
    expiring = [c for c in contracts if c.status == "Expiring Soon"]
    scores   = [c.vendor_score for c in contracts if c.vendor_score]
    total_value = sum(c.contract_value or 0 for c in active)
    avg_score   = round(sum(scores) / len(scores), 1) if scores else "N/A"

    return {
        "active_contracts":   len(active),
        "expiring_contracts": len(expiring),
        "total_contract_value": total_value,
        "avg_vendor_score":   avg_score,
    }
