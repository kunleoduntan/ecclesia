# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Audit Checklist Template Item — child table controller.
Auto-suggests COSO component and IIA standard reference
based on the selected control area.
"""

from frappe.model.document import Document


# Mapping: control area → (COSO component, IIA standard reference)
CONTROL_AREA_DEFAULTS = {
    "Completeness":           ("Control Activities",          "IIA 2320 – Analysis and Evaluation"),
    "Accuracy":               ("Control Activities",          "IIA 2320 – Analysis and Evaluation"),
    "GL Posting":             ("Control Activities",          "IIA 2310 – Identifying Information"),
    "Authorization":          ("Control Environment",         "IIA 2130 – Control"),
    "Cutoff":                 ("Control Activities",          "IIA 2320 – Analysis and Evaluation"),
    "Valuation":              ("Control Activities",          "IIA 2320 – Analysis and Evaluation"),
    "Existence":              ("Control Activities",          "IIA 2310 – Identifying Information"),
    "Segregation of Duties":  ("Control Environment",         "IIA 2130 – Control"),
    "Compliance":             ("Monitoring",                  "IIA 2120 – Risk Management"),
    "Three-way Match":        ("Control Activities",          "IIA 2130 – Control"),
    "Duplicate Payments":     ("Control Activities",          "IIA 2130 – Control"),
    "General Controls":       ("Control Environment",         "IIA 2110 – Governance"),
    "Data Integrity":         ("Information & Communication", "IIA 2310 – Identifying Information"),
    "Other":                  ("Risk Assessment",             "IIA 2120 – Risk Management"),
}


class AuditChecklistTemplateItem(Document):

    def validate(self):
        if self.control_area and self.control_area in CONTROL_AREA_DEFAULTS:
            coso, iia = CONTROL_AREA_DEFAULTS[self.control_area]
            if not self.coso_component:
                self.coso_component = coso
            if not self.iia_standard:
                self.iia_standard = iia