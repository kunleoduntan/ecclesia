# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Auditable DocType Registry Controller
======================================
This is the intelligence engine. When a new DocType JSON is registered,
this controller auto-classifies it, assigns a transaction code, maps fields,
detects GL posting capability, and generates an AI risk profile.

Register once → audit forever.
"""

import frappe
import json
import re
from frappe.model.document import Document
from ecclesia.utils.field_classifier import classify_fields, detect_gl_posting
from ecclesia.utils.transaction_coder import assign_transaction_code
from ecclesia.utils.ai_engine import generate_doctype_risk_profile
from ecclesia.utils.checklist_generator import create_default_checklist_template


class AuditableDocTypeRegistry(Document):

    def before_save(self):
        """Process DocType JSON on save if provided."""
        if self.doctype_json:
            self._process_doctype_json()
        if not self.registration_date:
            self.registration_date = frappe.utils.now()

    def after_insert(self):
        """After first registration, create default checklist template."""
        frappe.enqueue(
            "ecclesia.utils.checklist_generator.create_default_checklist_template",
            registry_name=self.name,
            doctype_name=self.doctype_name,
            classification=self.doctype_classification,
            queue="long"
        )
        # Update audit universe stats
        frappe.enqueue(
            "ecclesia.utils.ai_engine.refresh_single_doctype_stats",
            doctype_name=self.doctype_name,
            queue="default"
        )

    def _process_doctype_json(self):
        """
        Core intelligence: parse the DocType JSON and auto-populate
        all classification, field mapping, and risk profile fields.
        """
        try:
            dt_def = json.loads(self.doctype_json)
        except Exception:
            frappe.throw("Invalid JSON. Please paste a valid Frappe DocType JSON.")

        fields = dt_def.get("fields", [])
        doctype_name = dt_def.get("name", self.doctype_name)

        # Set doctype name and label from JSON
        self.doctype_name = doctype_name
        self.doctype_label = dt_def.get("name", doctype_name)

        # ── Field Classification ──────────────────────────────────────────
        classified = classify_fields(fields)

        self.amount_fields     = ", ".join(classified["amount_fields"])
        self.date_fields       = ", ".join(classified["date_fields"])
        self.approval_fields   = ", ".join(classified["approval_fields"])
        self.party_fields      = ", ".join(classified["party_fields"])
        self.account_fields    = ", ".join(classified["account_fields"])
        self.cost_center_fields= ", ".join(classified["cost_center_fields"])
        self.status_fields     = ", ".join(classified["status_fields"])
        self.user_fields       = ", ".join(classified["user_fields"])

        # ── DocType Classification ────────────────────────────────────────
        self.doctype_classification = _infer_classification(
            doctype_name, fields, classified
        )

        # ── GL Detection ─────────────────────────────────────────────────
        self.is_gl_posting = 1 if detect_gl_posting(dt_def, classified) else 0

        # ── Financial Statement Line ──────────────────────────────────────
        if self.is_gl_posting:
            self.financial_statement_line = _map_financial_statement(
                doctype_name, self.doctype_classification
            )
            self.account_class = _derive_account_class(self.financial_statement_line)

        # ── Transaction Code ─────────────────────────────────────────────
        if not self.transaction_code:
            codes = assign_transaction_code(
                doctype_name,
                self.doctype_classification,
                self.account_class or "",
                self.is_gl_posting
            )
            self.transaction_code = codes["full_code"]
            self.module_code      = codes["module_code"]
            self.type_code        = codes["type_code"]

        # ── Risk Level ───────────────────────────────────────────────────
        self.risk_level = _assess_inherent_risk(
            self.doctype_classification,
            self.is_gl_posting,
            classified
        )

        # ── Audit Frequency ──────────────────────────────────────────────
        self.audit_frequency = _recommend_frequency(self.risk_level)

        # ── COSO Component ───────────────────────────────────────────────
        self.coso_component = _map_coso_component(self.doctype_classification)

        # ── Sampling Method ──────────────────────────────────────────────
        self.sampling_method = _recommend_sampling(
            self.is_gl_posting, self.risk_level
        )

        # ── Materiality Benchmark ─────────────────────────────────────────
        self.materiality_benchmark = _recommend_materiality_benchmark(
            self.doctype_classification
        )

        # ── Recommended Sample Size ───────────────────────────────────────
        self.recommended_sample_size = _recommend_sample_size(
            self.risk_level, self.sampling_method
        )

        # ── AI Risk Profile (rule-based, works offline) ───────────────────
        profile = generate_doctype_risk_profile(
            doctype_name=doctype_name,
            classification=self.doctype_classification,
            classified_fields=classified,
            is_gl_posting=self.is_gl_posting,
            risk_level=self.risk_level
        )
        self.ai_risk_summary  = profile["risk_summary"]
        self.ai_key_controls  = profile["key_controls"]
        self.ai_red_flags     = profile["red_flags"]
        self.last_ai_refresh  = frappe.utils.now()

        frappe.msgprint(
            f"✅ DocType <b>{doctype_name}</b> processed successfully.<br>"
            f"Transaction Code: <b>{self.transaction_code}</b><br>"
            f"Classification: <b>{self.doctype_classification}</b><br>"
            f"Risk Level: <b>{self.risk_level}</b><br>"
            f"GL Posting: <b>{'Yes' if self.is_gl_posting else 'No'}</b>",
            title="DocType Registered",
            indicator="green"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helper classification functions
# ─────────────────────────────────────────────────────────────────────────────

def _infer_classification(doctype_name, fields, classified):
    """Infer DocType classification from name and field patterns."""
    name_lower = doctype_name.lower()

    # Name-based heuristics
    if any(k in name_lower for k in ["invoice", "payment", "journal", "ledger",
                                      "account", "tax", "expense", "budget",
                                      "asset", "depreciation"]):
        return "Financial"

    if any(k in name_lower for k in ["employee", "salary", "payroll", "leave",
                                      "attendance", "appraisal", "hr"]):
        return "HR & Payroll"

    if any(k in name_lower for k in ["stock", "inventory", "item", "warehouse",
                                      "bom", "material"]):
        return "Inventory & Stock"

    if any(k in name_lower for k in ["purchase", "supplier", "vendor", "rfq",
                                      "quotation", "po "]):
        return "Procurement"

    if any(k in name_lower for k in ["sales", "customer", "order", "delivery",
                                      "crm", "lead", "opportunity"]):
        return "Sales"

    # Field-based fallback
    if classified["amount_fields"] and classified["account_fields"]:
        return "Financial"
    if classified["amount_fields"] and classified["approval_fields"]:
        return "Procurement"
    if len(classified["approval_fields"]) > 2:
        return "Approval & Workflow"

    return "Custom"


def _map_financial_statement(doctype_name, classification):
    name_lower = doctype_name.lower()
    mapping = {
        "sales invoice":        "Income Statement - Revenue",
        "purchase invoice":     "Income Statement - Cost of Sales",
        "payment entry":        "Cash Flow - Operating",
        "journal entry":        "Balance Sheet - Equity",
        "expense claim":        "Income Statement - Operating Expense",
        "salary slip":          "Income Statement - Operating Expense",
        "asset":                "Balance Sheet - Asset",
        "purchase order":       "Balance Sheet - Liability",
        "sales order":          "Balance Sheet - Asset",
        "stock entry":          "Balance Sheet - Asset",
    }
    for key, val in mapping.items():
        if key in name_lower:
            return val

    if classification == "Financial":
        return "Balance Sheet - Asset"
    if classification == "HR & Payroll":
        return "Income Statement - Operating Expense"
    return "Not Applicable"


def _derive_account_class(financial_statement_line):
    mapping = {
        "Balance Sheet - Asset":             "ASSET",
        "Balance Sheet - Liability":         "LIAB",
        "Balance Sheet - Equity":            "EQUITY",
        "Income Statement - Revenue":        "REV",
        "Income Statement - Cost of Sales":  "COGS",
        "Income Statement - Operating Expense": "OPEX",
        "Income Statement - Other Income":   "OTHINC",
        "Cash Flow - Operating":             "CASH",
        "Cash Flow - Investing":             "INVEST",
        "Cash Flow - Financing":             "FIN",
    }
    return mapping.get(financial_statement_line, "NA")


def _assess_inherent_risk(classification, is_gl_posting, classified):
    score = 0

    if is_gl_posting:
        score += 3
    if classification == "Financial":
        score += 3
    if classification == "HR & Payroll":
        score += 2
    if len(classified["amount_fields"]) > 3:
        score += 2
    if len(classified["approval_fields"]) > 0:
        score += 1
    if len(classified["account_fields"]) > 0:
        score += 1

    if score >= 7:
        return "Critical"
    elif score >= 5:
        return "High"
    elif score >= 3:
        return "Medium"
    return "Low"


def _recommend_frequency(risk_level):
    return {
        "Critical": "Monthly",
        "High":     "Quarterly",
        "Medium":   "Semi-Annual",
        "Low":      "Annual",
    }.get(risk_level, "Annual")


def _map_coso_component(classification):
    return {
        "Financial":          "Control Activities",
        "HR & Payroll":       "Control Environment",
        "Inventory & Stock":  "Control Activities",
        "Procurement":        "Risk Assessment",
        "Sales":              "Control Activities",
        "Approval & Workflow":"Information & Communication",
        "Master Data":        "Control Environment",
        "Custom":             "Monitoring",
    }.get(classification, "Monitoring")


def _recommend_sampling(is_gl_posting, risk_level):
    if is_gl_posting and risk_level in ("Critical", "High"):
        return "Monetary Unit Sampling (MUS)"
    if risk_level == "Critical":
        return "100% Population"
    if is_gl_posting:
        return "Monetary Unit Sampling (MUS)"
    if risk_level == "Low":
        return "Judgmental"
    return "Random Statistical"


def _recommend_materiality_benchmark(classification):
    if classification == "Financial":
        return "Total Revenue"
    if classification in ("Procurement", "Inventory & Stock"):
        return "Total Expenses"
    if classification == "HR & Payroll":
        return "Total Expenses"
    return "Not Applicable"


def _recommend_sample_size(risk_level, sampling_method):
    if "100%" in sampling_method:
        return 100
    return {
        "Critical": 25,
        "High":     20,
        "Medium":   15,
        "Low":      10,
    }.get(risk_level, 15)
