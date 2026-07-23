# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    flt, getdate, nowdate, add_months, get_last_day,
    date_diff, cint, today, format_date, add_days, now_datetime,
    get_first_day, month_diff, get_datetime, money_in_words
)
import json
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta

# ============================================================================
# CONFIRMED FIELD NAMES (all verified from DocType JSONs)
# ============================================================================
# Fixed Asset Maintenance   → link: "asset", status field: "status"
# Fixed Asset Transfer Item → link: "asset", parent: "Fixed Asset Transfer"
# Fixed Asset Insurance     → link: "asset", status field: "policy_status"
# Fixed Asset Lease         → link: "asset", status field: "lease_status"
# Fixed Asset Revaluation   → link: "asset", amount field: "revaluation_amount"
# Fixed Asset Disposal      → link: "asset", scrap: disposal_type = 'Scrap'
# Depreciation Schedule Details → closing_balance, opening_balance, period_number,
#                                  status (Scheduled/Posted/Cancelled), journal_entry
# Fixed Asset Category      → frequency_of_depreciation: "1","3","6","12" (numeric)
#                              converted to "Monthly/Quarterly/Half-Yearly/Yearly"
#                              via CATEGORY_FREQUENCY_MAP before assigning to asset
# Asset History Log         → child of Fixed Asset, parentfield: "asset_history_log"
#                              columns: transaction_date, date, action, transaction_type,
#                              description, user, reference_doctype, reference_name,
#                              value_change, transaction_reference,
#                              transaction_reference_doctype
# ============================================================================

# Converts Fixed Asset Category's numeric frequency to Fixed Asset's text frequency
CATEGORY_FREQUENCY_MAP = {
    "1": "Monthly",
    "3": "Quarterly",
    "6": "Half-Yearly",
    "12": "Yearly",
    # Also handle if already text
    "Monthly": "Monthly",
    "Quarterly": "Quarterly",
    "Half-Yearly": "Half-Yearly",
    "Yearly": "Yearly",
}


class FixedAsset(Document):

    # ============================================================================
    # LIFECYCLE HOOKS
    # ============================================================================

    def before_insert(self):
        """Generate asset code and set initial values before insert"""
        if not self.asset_code:
            self.asset_code = self.generate_asset_code()

        if not self.company:
            self.company = frappe.defaults.get_user_default("Company")

    def validate(self):
        """Comprehensive validation"""
        self.validate_dates()
        self.validate_purchase_amount()
        self.load_category_defaults()
        self.validate_category_settings()
        self.validate_accounts()
        self.set_opening_values()
        self.calculate_depreciation_values()
        self.validate_depreciation_parameters()
        self.calculate_current_value()
        self.set_status()
        self.validate_disposal()
        self.validate_split_qty()
        self.intelligent_validation()

    def before_save(self):
        """Before save recalculations — no history log here"""
        self.calculate_current_value()
        self.update_depreciation_percentage()

    def on_submit(self):
        """
        On submit operations.
        NOTE: Depreciation schedule is NOT created here.
              It is triggered by the JS '📅 Generate Schedule' button.
        """
        self.validate_required_for_submit()
        self.set_status()
        self.generate_qr_code()
        self.update_asset_status("Active")
        self.log_asset_history("Submitted", f"Asset {self.asset_code} activated")
        frappe.msgprint(
            _("Asset {0} has been successfully activated").format(frappe.bold(self.asset_code)),
            indicator="green", alert=True
        )

    def on_cancel(self):
        """On cancel — reverse all entries"""
        self.validate_cancellation()
        self.cancel_depreciation_entries()
        self.cancel_related_documents()
        # Use db_set directly: "Cancelled" is not a valid Select option in the field
        # so bypassing via db_set is intentional to avoid validation error
        frappe.db.set_value("Fixed Asset", self.name, "asset_status", "Cancelled",
                            update_modified=False)
        self.asset_status = "Cancelled"
        self.log_asset_history("Cancelled", f"Asset {self.asset_code} cancelled")
        frappe.msgprint(
            _("Asset {0} has been cancelled. All related entries have been reversed").format(
                frappe.bold(self.asset_code)),
            indicator="orange", alert=True
        )

    def on_update_after_submit(self):
        """Post-submit recalculations"""
        self.calculate_current_value()
        self.update_depreciation_percentage()

    def on_trash(self):
        """Before deletion — ensure no dependencies exist"""
        self.validate_deletion()

    # ============================================================================
    # ASSET CODE GENERATION
    # ============================================================================

    def generate_asset_code(self):
        """Generate unique asset code: PREFIX-YYYY-00001"""
        if not self.asset_category:
            frappe.throw(_("Asset Category is required to generate Asset Code"))

        category = frappe.get_cached_doc("Fixed Asset Category", self.asset_category)
        prefix = category.get("asset_code_prefix") or "FA"

        last_code = frappe.db.sql("""
            SELECT asset_code
            FROM `tabFixed Asset`
            WHERE asset_code LIKE %s AND company = %s
            ORDER BY creation DESC
            LIMIT 1
        """, (f"{prefix}-%", self.company or ""), as_dict=False)

        if last_code:
            try:
                last_number = int(last_code[0][0].split("-")[-1])
                new_number = last_number + 1
            except Exception:
                new_number = 1
        else:
            new_number = 1

        year = getdate(self.purchase_date).year if self.purchase_date else getdate(nowdate()).year
        asset_code = f"{prefix}-{year}-{str(new_number).zfill(5)}"

        while frappe.db.exists("Fixed Asset", asset_code):
            new_number += 1
            asset_code = f"{prefix}-{year}-{str(new_number).zfill(5)}"

        return asset_code

    # ============================================================================
    # CATEGORY DEFAULTS AND SETTINGS
    # ============================================================================

    def load_category_defaults(self):
        """
        Load defaults from Fixed Asset Category (only fills in blanks).

        IMPORTANT: Fixed Asset Category stores frequency_of_depreciation as
        numeric strings "1","3","6","12". Fixed Asset stores depreciation_frequency
        as text "Monthly","Quarterly","Half-Yearly","Yearly". We convert here.
        """
        if not self.asset_category:
            return

        category = frappe.get_cached_doc("Fixed Asset Category", self.asset_category)

        if not self.asset_account:
            self.asset_account = category.get("fixed_asset_account")

        if not self.accumulated_depreciation_account and category.get("enable_depreciation"):
            self.accumulated_depreciation_account = category.get("accumulated_depreciation_account")

        if not self.depreciation_expense_account and category.get("enable_depreciation"):
            self.depreciation_expense_account = category.get("depreciation_expense_account")

        if self.calculate_depreciation and category.get("enable_depreciation"):
            if not self.depreciation_method:
                self.depreciation_method = category.get("depreciation_method") or "Straight Line"

            if not self.total_number_of_depreciations:
                self.total_number_of_depreciations = category.get("total_number_of_depreciations")

            if not self.depreciation_frequency:
                # BUG FIX: category stores "1","3","6","12" — convert to text
                cat_freq = str(category.get("frequency_of_depreciation") or "")
                self.depreciation_frequency = CATEGORY_FREQUENCY_MAP.get(cat_freq, "Monthly")

            if not self.depreciation_rate and category.get("rate_of_depreciation"):
                self.depreciation_rate = category.get("rate_of_depreciation")

            if not self.useful_life_months and category.get("useful_life_months"):
                self.useful_life_months = category.get("useful_life_months")

    def validate_category_settings(self):
        """Validate that the category supports the depreciation configuration chosen"""
        if not self.asset_category:
            frappe.throw(_("Asset Category is required"))

        category = frappe.get_cached_doc("Fixed Asset Category", self.asset_category)

        if self.calculate_depreciation:
            if not category.get("enable_depreciation"):
                frappe.throw(_("Depreciation is not enabled for Asset Category {0}").format(
                    frappe.bold(self.asset_category)))

            if not self.asset_account:
                frappe.throw(_("Asset Account is required for category {0}").format(
                    self.asset_category))

            if not self.accumulated_depreciation_account:
                frappe.throw(_("Accumulated Depreciation Account is required for depreciable assets"))

            if not self.depreciation_expense_account:
                frappe.throw(_("Depreciation Expense Account is required for depreciable assets"))

    # ============================================================================
    # DATE AND AMOUNT VALIDATIONS
    # ============================================================================

    def validate_dates(self):
        """Validate date logic"""
        if self.purchase_date and self.available_for_use_date:
            if getdate(self.available_for_use_date) < getdate(self.purchase_date):
                frappe.throw(_("Available for Use Date cannot be before Purchase Date"))

        # BUG FIX: guard against purchase_date being None
        if self.disposal_date and self.purchase_date:
            if getdate(self.disposal_date) < getdate(self.purchase_date):
                frappe.throw(_("Disposal Date cannot be before Purchase Date"))

            if self.available_for_use_date and getdate(self.disposal_date) < getdate(self.available_for_use_date):
                frappe.throw(_("Disposal Date cannot be before Available for Use Date"))

        if self.warranty_expiry_date and self.purchase_date:
            if getdate(self.warranty_expiry_date) < getdate(self.purchase_date):
                frappe.throw(_("Warranty Expiry Date cannot be before Purchase Date"))

        if self.insurance_expiry_date and self.purchase_date:
            if getdate(self.insurance_expiry_date) < getdate(self.purchase_date):
                frappe.throw(_("Insurance Expiry Date cannot be before Purchase Date"))

    def validate_purchase_amount(self):
        """Validate purchase and related amounts"""
        if flt(self.gross_purchase_amount) <= 0:
            frappe.throw(_("Gross Purchase Amount must be greater than zero"))

        if self.salvage_value and flt(self.salvage_value) >= flt(self.gross_purchase_amount):
            frappe.throw(_("Salvage Value cannot be greater than or equal to Gross Purchase Amount"))

        if self.insurance_value and flt(self.insurance_value) > flt(self.gross_purchase_amount) * 2:
            frappe.msgprint(
                _("Insurance Value ({0}) seems unusually high compared to Purchase Amount ({1})").format(
                    frappe.bold(self.insurance_value), frappe.bold(self.gross_purchase_amount)),
                indicator="orange", alert=True
            )

    def validate_accounts(self):
        """Validate that all accounts belong to the correct company"""
        if not self.company:
            frappe.throw(_("Company is required"))

        if self.asset_account:
            account = frappe.get_cached_doc("Account", self.asset_account)
            if account.company != self.company:
                frappe.throw(_("Asset Account {0} does not belong to Company {1}").format(
                    self.asset_account, self.company))

            if account.account_type != "Fixed Asset":
                frappe.msgprint(
                    _("Asset Account {0} is not of type 'Fixed Asset'").format(self.asset_account),
                    indicator="orange"
                )

        if self.calculate_depreciation:
            if self.accumulated_depreciation_account:
                acc = frappe.get_cached_doc("Account", self.accumulated_depreciation_account)
                if acc.company != self.company:
                    frappe.throw(_("Accumulated Depreciation Account does not belong to Company {0}").format(
                        self.company))

            if self.depreciation_expense_account:
                acc = frappe.get_cached_doc("Account", self.depreciation_expense_account)
                if acc.company != self.company:
                    frappe.throw(_("Depreciation Expense Account does not belong to Company {0}").format(
                        self.company))

    # ============================================================================
    # OPENING VALUES AND CALCULATIONS
    # ============================================================================

    def set_opening_values(self):
        """Set opening values once when first created"""
        if self.is_new():
            self.opening_gross_value = flt(self.gross_purchase_amount)
            self.current_gross_value = flt(self.gross_purchase_amount)

            if self.is_existing_asset:
                if not self.opening_accumulated_depreciation:
                    self.opening_accumulated_depreciation = 0
                self.current_accumulated_depreciation = flt(self.opening_accumulated_depreciation)
            else:
                self.opening_accumulated_depreciation = 0
                self.current_accumulated_depreciation = 0

            self.current_net_book_value = (
                flt(self.current_gross_value) - flt(self.current_accumulated_depreciation)
            )

    # ============================================================================
    # DEPRECIATION CALCULATIONS
    # ============================================================================

    def calculate_depreciation_values(self):
        """Calculate all depreciation-related values with intelligent defaults"""
        if not self.calculate_depreciation:
            return

        if not self.depreciation_method:
            frappe.throw(_("Depreciation Method is required when Calculate Depreciation is checked"))

        # Keep salvage_value and residual_value in sync
        if not self.salvage_value and self.residual_value:
            self.salvage_value = flt(self.residual_value)
        elif not self.residual_value and self.salvage_value:
            self.residual_value = flt(self.salvage_value)
        elif not self.salvage_value and not self.residual_value:
            self.salvage_value = flt(self.gross_purchase_amount) * 0.10
            self.residual_value = self.salvage_value

        self.depreciable_amount = flt(self.gross_purchase_amount) - flt(self.salvage_value)

        if not self.depreciation_start_date:
            self.depreciation_start_date = self.available_for_use_date or self.purchase_date

        frequency_months = self.get_frequency_months()

        if self.total_number_of_depreciations:
            self.total_depreciation_months = cint(self.total_number_of_depreciations) * frequency_months
            if not self.useful_life_months:
                self.useful_life_months = self.total_depreciation_months
        elif self.useful_life_months:
            self.total_number_of_depreciations = cint(self.useful_life_months / frequency_months)
            self.total_depreciation_months = self.useful_life_months

        self.calculate_depreciation_rate()

    def get_frequency_months(self):
        """Return the number of months in each depreciation period"""
        frequency_map = {
            "Monthly": 1,
            "Quarterly": 3,
            "Half-Yearly": 6,
            "Yearly": 12
        }
        return frequency_map.get(self.depreciation_frequency, 1)

    def calculate_depreciation_rate(self):
        """Auto-calculate the depreciation rate if not already set"""
        if not self.total_number_of_depreciations or self.total_number_of_depreciations <= 0:
            return

        if self.depreciation_method == "Straight Line":
            if not self.depreciation_rate:
                self.depreciation_rate = flt(100.0 / self.total_number_of_depreciations, 2)

        elif self.depreciation_method == "Written Down Value":
            if not self.depreciation_rate and self.total_depreciation_months:
                years = flt(self.total_depreciation_months) / 12
                if (years > 0
                        and flt(self.gross_purchase_amount) > 0
                        and flt(self.salvage_value) < flt(self.gross_purchase_amount)):
                    try:
                        ratio = flt(self.salvage_value) / flt(self.gross_purchase_amount)
                        if ratio > 0:
                            self.depreciation_rate = flt((1 - pow(ratio, 1.0 / years)) * 100, 2)
                    except Exception:
                        self.depreciation_rate = 20.0

        elif self.depreciation_method == "Double Declining Balance":
            if not self.depreciation_rate and self.total_depreciation_months:
                years = flt(self.total_depreciation_months) / 12
                if years > 0:
                    self.depreciation_rate = flt((2.0 / years) * 100, 2)

    def validate_depreciation_parameters(self):
        """Validate that all required depreciation parameters are present and sensible"""
        if not self.calculate_depreciation:
            return

        if not self.total_number_of_depreciations and not self.useful_life_months:
            frappe.throw(_(
                "Either Total Number of Depreciations or Useful Life (Months) is required"
            ))

        if not self.depreciation_frequency:
            frappe.throw(_("Depreciation Frequency is required"))

        if not self.depreciation_rate or flt(self.depreciation_rate) <= 0:
            frappe.throw(_("Depreciation Rate must be greater than zero"))

        if flt(self.depreciation_rate) > 100:
            frappe.throw(_("Depreciation Rate cannot exceed 100%"))

        if self.is_existing_asset:
            if flt(self.opening_accumulated_depreciation) >= flt(self.gross_purchase_amount):
                frappe.throw(_(
                    "Opening Accumulated Depreciation cannot be greater than or equal "
                    "to Gross Purchase Amount"
                ))

    # ============================================================================
    # CURRENT VALUE CALCULATIONS
    # ============================================================================

    def calculate_current_value(self):
        """
        Calculate the real-time net book value.
        Draft: derive from in-memory fields.
        Submitted: sum posted JEs from the depreciation schedule.
        """
        if self.docstatus == 0:
            self.current_net_book_value = (
                flt(self.current_gross_value) - flt(self.current_accumulated_depreciation)
            )
        else:
            total_posted = frappe.db.sql("""
                SELECT IFNULL(SUM(depreciation_amount), 0)
                FROM `tabDepreciation Schedule Details`
                WHERE parent = %s
                AND parenttype = 'Fixed Asset'
                AND journal_entry IS NOT NULL
                AND journal_entry != ''
            """, self.name)[0][0] or 0

            self.current_accumulated_depreciation = (
                flt(self.opening_accumulated_depreciation) + flt(total_posted)
            )

            total_revaluation = self.get_total_revaluation()
            self.current_gross_value = flt(self.opening_gross_value) + flt(total_revaluation)
            self.total_revaluation_amount = flt(total_revaluation)

            self.current_net_book_value = (
                flt(self.current_gross_value) - flt(self.current_accumulated_depreciation)
            )

            if flt(self.current_net_book_value) < flt(self.salvage_value or 0):
                self.current_net_book_value = flt(self.salvage_value or 0)

    def get_total_revaluation(self):
        """
        Sum all submitted revaluation amounts for this asset.
        Confirmed doctype: "Fixed Asset Revaluation" (not "Asset Value Adjustment")
        Confirmed link field: "asset"
        Confirmed amount column: "revaluation_amount"
        """
        try:
            total = frappe.db.sql("""
                SELECT IFNULL(SUM(revaluation_amount), 0)
                FROM `tabFixed Asset Revaluation`
                WHERE asset = %s AND docstatus = 1
            """, self.name)[0][0] or 0
            return flt(total)
        except Exception:
            return 0.0

    def update_depreciation_percentage(self):
        """Recalculate depreciation progress percentage and completed months"""
        if flt(self.gross_purchase_amount) > 0:
            self.depreciation_percentage_complete = flt(
                (flt(self.current_accumulated_depreciation) /
                 flt(self.gross_purchase_amount)) * 100, 2
            )

        if self.depreciation_start_date and self.docstatus == 1:
            start = getdate(self.depreciation_start_date)
            current = getdate(nowdate())
            months_elapsed = month_diff(current, start)
            self.depreciation_completed_months = cint(months_elapsed) if months_elapsed > 0 else 0

    # ============================================================================
    # ASSET STATUS MANAGEMENT
    # ============================================================================

    def set_status(self):
        """
        Derive and set asset_status from the asset's current state.
        NOTE: "Cancelled" is not in the Select options — on_cancel uses db_set directly.
        """
        if self.docstatus == 0:
            self.asset_status = "Draft"
        elif self.docstatus == 2:
            # Cannot set via normal field: "Cancelled" not in Select options
            # on_cancel handles this via frappe.db.set_value() to bypass validation
            pass
        elif self.disposal_date:
            self.asset_status = "Disposed"
        elif (not self.available_for_use_date
              or getdate(self.available_for_use_date) > getdate(nowdate())):
            self.asset_status = "Draft"
        else:
            if self.is_under_maintenance():
                self.asset_status = "Under Maintenance"
            elif flt(self.current_net_book_value) <= flt(self.salvage_value or 0):
                self.asset_status = "Fully Depreciated"
            elif self.is_scrapped():
                self.asset_status = "Scrapped"
            elif self.is_in_transit():
                self.asset_status = "Transferred"
            else:
                self.asset_status = "Active"

    def is_under_maintenance(self):
        """
        Return True if there is an in-progress maintenance record for this asset.

        Doctype confirmed: "Fixed Asset Maintenance"
        Link field confirmed: "asset" (from Fixed Asset Maintenance JSON)
        Status field confirmed: includes "In Progress"

        Raw SQL used because frappe.db.count() with ORM filters cannot handle
        status filtering reliably across all Frappe versions.
        """
        if self.docstatus != 1:
            return False
        try:
            count = frappe.db.sql("""
                SELECT COUNT(*)
                FROM `tabFixed Asset Maintenance`
                WHERE asset = %s AND status = 'In Progress'
            """, self.name)[0][0]
            return cint(count) > 0
        except Exception:
            return False

    def is_scrapped(self):
        """
        Return True if this asset has a submitted Scrap disposal record.
        Confirmed: no separate Asset Scrap doctype exists.
        Scrap is tracked via Fixed Asset Disposal with disposal_type = 'Scrap'.
        Link field confirmed: "asset" (from Fixed Asset Disposal JSON)
        """
        try:
            count = frappe.db.sql("""
                SELECT COUNT(*)
                FROM `tabFixed Asset Disposal`
                WHERE asset = %s AND docstatus = 1 AND disposal_type = 'Scrap'
            """, self.name)[0][0]
            return cint(count) > 0
        except Exception:
            return False

    def is_in_transit(self):
        """
        Return True if there is a submitted Transfer record for this asset.
        Confirmed: Uses Fixed Asset Transfer (not ERPNext's Asset Movement).
        Child table: Fixed Asset Transfer Item, link field: "asset" (confirmed from JSON)
        Parent: Fixed Asset Transfer, link via .parent
        """
        try:
            count = frappe.db.sql("""
                SELECT COUNT(*)
                FROM `tabFixed Asset Transfer Item` fati
                INNER JOIN `tabFixed Asset Transfer` fat ON fat.name = fati.parent
                WHERE fati.asset = %s AND fat.docstatus = 1
            """, self.name)[0][0]
            return cint(count) > 0
        except Exception:
            return False

    def update_asset_status(self, status):
        """
        Persist a new status and log the change.
        Uses db_set with update_modified=False to avoid triggering modified timestamp.
        """
        old_status = self.asset_status
        self.asset_status = status
        # Use direct db_set to bypass Select field validation for "Cancelled"
        frappe.db.set_value("Fixed Asset", self.name, "asset_status", status,
                            update_modified=False)

        if old_status != status:
            self.log_asset_history(
                "Status Change",
                f"Status changed from {old_status} to {status}"
            )

    # ============================================================================
    # VALIDATION CHECKS
    # ============================================================================

    def validate_disposal(self):
        """
        Block disposal if active leases or maintenance tasks exist.

        Confirmed doctypes and fields:
          Fixed Asset Lease     → link: "asset", status: "lease_status", active: "Active"
          Fixed Asset Maintenance → link: "asset", status: "status", active: "In Progress"
        """
        if not self.disposal_date:
            return

        # Check active leases (confirmed: "Fixed Asset Lease", field: "asset", status: "lease_status")
        try:
            active_leases = frappe.db.sql("""
                SELECT COUNT(*) FROM `tabFixed Asset Lease`
                WHERE asset = %s AND docstatus = 1 AND lease_status = 'Active'
            """, self.name)[0][0]
            if cint(active_leases) > 0:
                frappe.throw(_("Cannot dispose asset with active lease agreements"))
        except frappe.ValidationError:
            raise
        except Exception:
            pass

        # Check active maintenance (confirmed: "Fixed Asset Maintenance", field: "asset")
        try:
            active_maintenance = frappe.db.sql("""
                SELECT COUNT(*) FROM `tabFixed Asset Maintenance`
                WHERE asset = %s AND status = 'In Progress'
            """, self.name)[0][0]
            if cint(active_maintenance) > 0:
                frappe.throw(_("Cannot dispose asset with ongoing maintenance tasks"))
        except frappe.ValidationError:
            raise
        except Exception:
            pass

    def validate_split_qty(self):
        """Asset Quantity must be >= 1"""
        if self.asset_quantity and flt(self.asset_quantity) < 1:
            frappe.throw(_("Asset Quantity must be at least 1"))

    def validate_required_for_submit(self):
        """Block submission if critical fields are missing"""
        required_fields = {
            "available_for_use_date": _("Available for Use Date"),
            "cost_center": _("Cost Center"),
            "asset_account": _("Asset Account"),
        }

        missing = []
        for field, label in required_fields.items():
            if not self.get(field):
                missing.append(label)

        if missing:
            frappe.throw(_("The following fields are required for submission: {0}").format(
                ", ".join(missing)))

        if self.calculate_depreciation:
            dep_required = {
                "depreciation_method": _("Depreciation Method"),
                "total_number_of_depreciations": _("Total Number of Depreciations"),
                "depreciation_frequency": _("Depreciation Frequency"),
                "accumulated_depreciation_account": _("Accumulated Depreciation Account"),
                "depreciation_expense_account": _("Depreciation Expense Account"),
            }
            dep_missing = [lbl for fld, lbl in dep_required.items() if not self.get(fld)]
            if dep_missing:
                frappe.throw(_("The following depreciation fields are required: {0}").format(
                    ", ".join(dep_missing)))

    def validate_cancellation(self):
        """
        Block cancellation if dependent active records exist.

        All confirmed doctypes and fields:
          Fixed Asset Transfer Item → JOIN Fixed Asset Transfer, link: "asset"
          Fixed Asset Maintenance   → link: "asset", status field: "status"
          Fixed Asset Insurance     → link: "asset", status field: "policy_status"
          Fixed Asset Lease         → link: "asset", status field: "lease_status"
        """
        # Inform user about posted depreciation entries that will be reversed
        try:
            posted_count = frappe.db.sql("""
                SELECT COUNT(*) FROM `tabDepreciation Schedule Details`
                WHERE parent = %s
                AND journal_entry IS NOT NULL AND journal_entry != ''
            """, self.name)[0][0]

            if cint(posted_count) > 0:
                frappe.msgprint(
                    _("This asset has {0} posted depreciation entries. "
                      "These will be automatically cancelled.").format(posted_count),
                    indicator="orange", alert=True
                )
        except Exception:
            pass

        # Block: active transfers (Fixed Asset Transfer Item JOIN Fixed Asset Transfer)
        try:
            active_transfers = frappe.db.sql("""
                SELECT COUNT(*)
                FROM `tabFixed Asset Transfer Item` fati
                INNER JOIN `tabFixed Asset Transfer` fat ON fat.name = fati.parent
                WHERE fati.asset = %s AND fat.docstatus = 1
            """, self.name)[0][0]
            if cint(active_transfers) > 0:
                frappe.throw(_(
                    "Cannot cancel asset with active transfer records. "
                    "Please cancel the transfers first."
                ))
        except frappe.ValidationError:
            raise
        except Exception:
            pass

        # Block: active maintenance (confirmed: "Fixed Asset Maintenance", status field: "status")
        try:
            active_maintenance = frappe.db.sql("""
                SELECT COUNT(*) FROM `tabFixed Asset Maintenance`
                WHERE asset = %s AND status IN ('Scheduled', 'In Progress')
            """, self.name)[0][0]
            if cint(active_maintenance) > 0:
                frappe.throw(_("Cannot cancel asset with active maintenance tasks"))
        except frappe.ValidationError:
            raise
        except Exception:
            pass

        # Block: active insurance (confirmed: "Fixed Asset Insurance", status field: "policy_status")
        try:
            active_insurance = frappe.db.sql("""
                SELECT COUNT(*) FROM `tabFixed Asset Insurance`
                WHERE asset = %s AND docstatus = 1 AND policy_status = 'Active'
            """, self.name)[0][0]
            if cint(active_insurance) > 0:
                frappe.throw(_("Cannot cancel asset with active insurance policies"))
        except frappe.ValidationError:
            raise
        except Exception:
            pass

        # Block: active leases (confirmed: "Fixed Asset Lease", status field: "lease_status")
        try:
            active_leases = frappe.db.sql("""
                SELECT COUNT(*) FROM `tabFixed Asset Lease`
                WHERE asset = %s AND docstatus = 1 AND lease_status = 'Active'
            """, self.name)[0][0]
            if cint(active_leases) > 0:
                frappe.throw(_("Cannot cancel asset with active lease agreements"))
        except frappe.ValidationError:
            raise
        except Exception:
            pass

    def validate_deletion(self):
        """Warn before deleting an asset that has child records"""
        if self.docstatus == 1:
            frappe.throw(_("Cannot delete submitted asset. Please cancel it first."))

        linked_docs = []

        if frappe.db.count("Depreciation Schedule Details", {"parent": self.name}):
            linked_docs.append("Depreciation Schedules")

        # Asset History Log is a child table — also stored inline
        try:
            if frappe.db.count("Asset History Log", {"parent": self.name}):
                linked_docs.append("History Logs")
        except Exception:
            pass

        if linked_docs:
            frappe.msgprint(
                _("Deleting this asset will also remove: {0}").format(", ".join(linked_docs)),
                indicator="orange"
            )

    def intelligent_validation(self):
        """Soft data-quality warnings shown as an orange alert"""
        warnings = []

        if flt(self.gross_purchase_amount) < 1000:
            warnings.append(
                _("Purchase amount seems unusually low ({0})").format(self.gross_purchase_amount)
            )

        if self.purchase_date:
            years_old = date_diff(nowdate(), self.purchase_date) / 365
            if years_old > 20:
                warnings.append(
                    _("Asset is {0} years old — consider reviewing its status").format(int(years_old))
                )

        if self.depreciation_rate and self.calculate_depreciation:
            if flt(self.depreciation_rate) > 50:
                warnings.append(
                    _("Depreciation rate of {0}% is unusually high").format(self.depreciation_rate)
                )
            elif flt(self.depreciation_rate) < 5:
                warnings.append(
                    _("Depreciation rate of {0}% is unusually low").format(self.depreciation_rate)
                )

        if self.warranty_expiry_date and getdate(self.warranty_expiry_date) < getdate(nowdate()):
            days_expired = date_diff(nowdate(), self.warranty_expiry_date)
            warnings.append(_("Warranty expired {0} days ago").format(days_expired))

        if self.insurance_expiry_date:
            days_to_expiry = date_diff(self.insurance_expiry_date, nowdate())
            if days_to_expiry < 0:
                warnings.append(_("Insurance expired {0} days ago").format(abs(days_to_expiry)))
            elif days_to_expiry < 30:
                warnings.append(_("Insurance expiring in {0} days").format(days_to_expiry))

        if warnings:
            # Use HTML entity &bull; to avoid encoding corruption
            frappe.msgprint(
                _("<b>Data Quality Warnings:</b><br>") + "<br>".join(
                    f"&bull; {w}" for w in warnings
                ),
                indicator="orange",
                title=_("Asset Validation Warnings")
            )

    # ============================================================================
    # QR CODE GENERATION
    # ============================================================================

    def generate_qr_code(self):
        """Generate a QR code PNG and attach it to this asset record"""
        if self.qr_code_image:
            return  # Already generated

        try:
            qr_data = {
                "asset_code": self.asset_code,
                "asset_name": self.asset_name,
                "category": self.asset_category,
                "company": self.company,
                "purchase_date": str(self.purchase_date) if self.purchase_date else "",
                "purchase_amount": flt(self.gross_purchase_amount),
                "current_value": flt(self.current_net_book_value),
                "location": self.current_location or "",
                "department": self.department or "",
                "custodian": self.custodian or "",
                "serial_no": self.serial_number or "",
                "status": self.asset_status,
                "url": f"{frappe.utils.get_url()}/app/fixed-asset/{self.name}"
            }

            qr_string = json.dumps(qr_data, indent=2)

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            file_name = f"QR_Code_{self.asset_code}.png"
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "attached_to_doctype": "Fixed Asset",
                "attached_to_name": self.name,
                "content": f"data:image/png;base64,{img_str}",
                "is_private": 0
            })
            file_doc.flags.ignore_permissions = True
            file_doc.insert()

            self.qr_code = qr_string
            self.qr_code_image = file_doc.file_url
            self.db_set("qr_code", qr_string, update_modified=False)
            self.db_set("qr_code_image", file_doc.file_url, update_modified=False)

            frappe.msgprint(_("QR Code generated successfully"), indicator="green")
            self.log_asset_history("QR Code", "QR code generated")

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"QR Code Generation Failed - {self.name}")
            frappe.msgprint(
                _("Warning: QR Code generation failed - {0}").format(str(e)),
                indicator="orange"
            )

    # ============================================================================
    # DEPRECIATION SCHEDULE CREATION
    # ============================================================================

    def create_depreciation_schedule(self):
        """
        Create the full depreciation schedule for this asset.
        Called from the JS '📅 Generate Schedule' button (NOT from on_submit).
        """
        if not self.calculate_depreciation:
            return

        if not self.available_for_use_date:
            frappe.throw(_("Available for Use Date is required to create depreciation schedule"))

        # Clear existing unposted schedule rows
        frappe.db.sql("""
            DELETE FROM `tabDepreciation Schedule Details`
            WHERE parent = %s AND parenttype = 'Fixed Asset'
            AND (journal_entry IS NULL OR journal_entry = '')
        """, self.name)

        schedule = self.get_depreciation_schedule()

        if not schedule:
            frappe.msgprint(
                _("No depreciation schedule created - asset may be fully depreciated"),
                indicator="orange"
            )
            return

        # Insert schedule rows via raw SQL (safer than frappe.get_doc().db_insert()
        # during post-submit operations)
        for idx, entry in enumerate(schedule, start=1):
            frappe.db.sql("""
                INSERT INTO `tabDepreciation Schedule Details`
                (name, parent, parenttype, parentfield, idx,
                 schedule_date, period_number, opening_balance,
                 depreciation_amount, accumulated_depreciation,
                 closing_balance, status,
                 creation, modified, modified_by, owner, docstatus)
                VALUES
                (%s, %s, %s, %s, %s,
                 %s, %s, %s,
                 %s, %s,
                 %s, %s,
                 NOW(), NOW(), %s, %s, 0)
            """, (
                frappe.generate_hash(length=10),
                self.name,
                "Fixed Asset",
                "depreciation_schedules",
                idx,
                entry["schedule_date"],
                entry["period_number"],
                entry["opening_balance"],
                entry["depreciation_amount"],
                entry["accumulated_depreciation"],
                entry["closing_balance"],   # confirmed field name (not net_book_value)
                "Scheduled",
                frappe.session.user,
                frappe.session.user,
            ))

        frappe.db.commit()

        # Set next depreciation date to first unposted row
        self.db_set("next_depreciation_date", schedule[0]["schedule_date"], update_modified=False)

        frappe.msgprint(
            _("Depreciation Schedule created with {0} entries").format(len(schedule)),
            indicator="green", alert=True
        )
        self.log_asset_history(
            "Schedule Created",
            f"Depreciation schedule created with {len(schedule)} entries"
        )

    def get_depreciation_schedule(self):
        """Dispatch to the correct schedule calculation method"""
        method_map = {
            "Straight Line": self.get_straight_line_schedule,
            "Written Down Value": self.get_wdv_schedule,
            "Double Declining Balance": self.get_ddb_schedule,
            "Units of Production": self.get_units_of_production_schedule,
            "Sum of Years Digits": self.get_sum_of_years_digits_schedule,
        }

        method_func = method_map.get(self.depreciation_method)
        if not method_func:
            frappe.throw(_("Unsupported depreciation method: {0}").format(self.depreciation_method))

        return method_func()

    def _build_schedule_entry(self, period_num, schedule_date, opening_nbv,
                               depreciation_amount, accumulated_depreciation):
        """
        Helper that returns a dict with the exact field names from
        Depreciation Schedule Details JSON.
        closing_balance = opening_nbv - depreciation_amount
        """
        closing = flt(opening_nbv) - flt(depreciation_amount)
        return {
            "period_number": period_num,
            "schedule_date": schedule_date,
            "opening_balance": flt(opening_nbv, 2),
            "depreciation_amount": flt(depreciation_amount, 2),
            "accumulated_depreciation": flt(accumulated_depreciation, 2),
            "closing_balance": flt(closing, 2),   # confirmed field name
        }

    def get_straight_line_schedule(self):
        """Calculate Straight Line depreciation schedule"""
        schedule = []

        start_date = getdate(self.depreciation_start_date)
        number_of_depreciations = cint(self.total_number_of_depreciations)
        frequency = self.get_frequency_months()

        depreciable_value = (
            flt(self.gross_purchase_amount)
            - flt(self.opening_accumulated_depreciation)
            - flt(self.salvage_value)
        )

        if depreciable_value <= 0:
            return []

        depreciation_per_period = flt(depreciable_value / number_of_depreciations, 2)
        accumulated_depreciation = flt(self.opening_accumulated_depreciation)
        book_value = flt(self.gross_purchase_amount) - accumulated_depreciation
        current_date = start_date

        for i in range(number_of_depreciations):
            if i == 0:
                schedule_date = get_last_day(add_months(start_date, frequency - 1))
            else:
                schedule_date = get_last_day(add_months(current_date, frequency))

            current_date = schedule_date
            depreciation_amount = depreciation_per_period

            # Last period: adjust to reach exact salvage value
            if i == number_of_depreciations - 1:
                depreciation_amount = book_value - flt(self.salvage_value)

            if book_value - depreciation_amount < flt(self.salvage_value):
                depreciation_amount = book_value - flt(self.salvage_value)

            if depreciation_amount <= 0:
                break

            opening_nbv = book_value
            accumulated_depreciation += depreciation_amount
            book_value -= depreciation_amount

            schedule.append(self._build_schedule_entry(
                i + 1, schedule_date, opening_nbv,
                depreciation_amount, accumulated_depreciation
            ))

            if book_value <= flt(self.salvage_value):
                break

        return schedule

    def get_wdv_schedule(self):
        """Calculate Written Down Value (Reducing Balance) depreciation schedule"""
        schedule = []

        start_date = getdate(self.depreciation_start_date)
        rate = flt(self.depreciation_rate) / 100
        number_of_depreciations = cint(self.total_number_of_depreciations)
        frequency = self.get_frequency_months()
        period_rate = rate * (frequency / 12)

        accumulated_depreciation = flt(self.opening_accumulated_depreciation)
        book_value = flt(self.gross_purchase_amount) - accumulated_depreciation
        current_date = start_date

        for i in range(number_of_depreciations):
            if i == 0:
                schedule_date = get_last_day(add_months(start_date, frequency - 1))
            else:
                schedule_date = get_last_day(add_months(current_date, frequency))

            current_date = schedule_date
            depreciation_amount = book_value * period_rate

            if book_value - depreciation_amount < flt(self.salvage_value):
                depreciation_amount = book_value - flt(self.salvage_value)

            if depreciation_amount <= 0:
                break

            opening_nbv = book_value
            accumulated_depreciation += depreciation_amount
            book_value -= depreciation_amount

            schedule.append(self._build_schedule_entry(
                i + 1, schedule_date, opening_nbv,
                depreciation_amount, accumulated_depreciation
            ))

            if book_value <= flt(self.salvage_value):
                break

        return schedule

    def get_ddb_schedule(self):
        """Calculate Double Declining Balance depreciation schedule"""
        schedule = []

        start_date = getdate(self.depreciation_start_date)
        number_of_depreciations = cint(self.total_number_of_depreciations)
        frequency = self.get_frequency_months()

        if self.total_depreciation_months:
            years = flt(self.total_depreciation_months) / 12
            ddb_rate = 2 / years if years > 0 else 0
            period_rate = ddb_rate * (frequency / 12)
        else:
            period_rate = 0

        accumulated_depreciation = flt(self.opening_accumulated_depreciation)
        book_value = flt(self.gross_purchase_amount) - accumulated_depreciation
        current_date = start_date

        for i in range(number_of_depreciations):
            if i == 0:
                schedule_date = get_last_day(add_months(start_date, frequency - 1))
            else:
                schedule_date = get_last_day(add_months(current_date, frequency))

            current_date = schedule_date
            depreciation_amount = book_value * period_rate

            # Switch to straight line if it gives a higher depreciation
            remaining_periods = number_of_depreciations - i
            if remaining_periods > 0:
                straight_line_amount = (book_value - flt(self.salvage_value)) / remaining_periods
                depreciation_amount = max(depreciation_amount, straight_line_amount)

            if book_value - depreciation_amount < flt(self.salvage_value):
                depreciation_amount = book_value - flt(self.salvage_value)

            if depreciation_amount <= 0:
                break

            opening_nbv = book_value
            accumulated_depreciation += depreciation_amount
            book_value -= depreciation_amount

            schedule.append(self._build_schedule_entry(
                i + 1, schedule_date, opening_nbv,
                depreciation_amount, accumulated_depreciation
            ))

            if book_value <= flt(self.salvage_value):
                break

        return schedule

    def get_sum_of_years_digits_schedule(self):
        """Calculate Sum of Years Digits depreciation schedule"""
        schedule = []

        start_date = getdate(self.depreciation_start_date)
        number_of_depreciations = cint(self.total_number_of_depreciations)
        frequency = self.get_frequency_months()
        sum_of_digits = (number_of_depreciations * (number_of_depreciations + 1)) / 2

        depreciable_value = (
            flt(self.gross_purchase_amount)
            - flt(self.opening_accumulated_depreciation)
            - flt(self.salvage_value)
        )

        if depreciable_value <= 0:
            return []

        accumulated_depreciation = flt(self.opening_accumulated_depreciation)
        book_value = flt(self.gross_purchase_amount) - accumulated_depreciation
        current_date = start_date

        for i in range(number_of_depreciations):
            if i == 0:
                schedule_date = get_last_day(add_months(start_date, frequency - 1))
            else:
                schedule_date = get_last_day(add_months(current_date, frequency))

            current_date = schedule_date
            remaining_life = number_of_depreciations - i
            depreciation_amount = (remaining_life / sum_of_digits) * depreciable_value

            if book_value - depreciation_amount < flt(self.salvage_value):
                depreciation_amount = book_value - flt(self.salvage_value)

            if depreciation_amount <= 0:
                break

            opening_nbv = book_value
            accumulated_depreciation += depreciation_amount
            book_value -= depreciation_amount

            schedule.append(self._build_schedule_entry(
                i + 1, schedule_date, opening_nbv,
                depreciation_amount, accumulated_depreciation
            ))

            if book_value <= flt(self.salvage_value):
                break

        return schedule

    def get_units_of_production_schedule(self):
        """Units of Production requires production tracking — not yet implemented"""
        frappe.msgprint(
            _("Units of Production method requires production tracking. Please use another method."),
            indicator="orange"
        )
        return []

    # ============================================================================
    # CANCELLATION AND REVERSAL
    # ============================================================================

    def cancel_depreciation_entries(self):
        """Cancel every posted depreciation JE linked to this asset's schedule"""
        schedules = frappe.get_all(
            "Depreciation Schedule Details",
            filters={
                "parent": self.name,
                "parenttype": "Fixed Asset",
                "journal_entry": ["not in", ["", None]]
            },
            fields=["name", "journal_entry"]
        )

        cancelled_count = 0
        for row in schedules:
            if not row.journal_entry:
                continue
            try:
                je = frappe.get_doc("Journal Entry", row.journal_entry)
                if je.docstatus == 1:
                    je.flags.ignore_permissions = True
                    je.cancel()
                    cancelled_count += 1

                # Clear JE reference and update status
                frappe.db.sql("""
                    UPDATE `tabDepreciation Schedule Details`
                    SET journal_entry = NULL, status = 'Cancelled'
                    WHERE name = %s
                """, row.name)

            except Exception as e:
                frappe.log_error(
                    frappe.get_traceback(), f"Failed to cancel JE {row.journal_entry}"
                )
                frappe.msgprint(
                    _("Warning: Could not cancel Journal Entry {0}").format(row.journal_entry),
                    indicator="orange"
                )

        if cancelled_count > 0:
            frappe.msgprint(
                _("Cancelled {0} depreciation entries").format(cancelled_count),
                indicator="blue"
            )

    def cancel_related_documents(self):
        """Placeholder — extend as additional modules are built"""
        self.log_asset_history("Cancellation", "Asset cancelled - related documents checked")

    # ============================================================================
    # ASSET HISTORY LOGGING
    # ============================================================================

    def log_asset_history(self, action, description, reference_doctype=None,
                          reference_name=None, transaction_type=None, value_change=None):
        """
        Insert a row into tabAsset History Log via raw SQL.

        Confirmed columns from Asset History Log JSON:
          transaction_date  Date     (reqd) — the calendar date
          date              Datetime (read_only) — timestamp, auto-set
          action            Data     — short action label
          transaction_type  Select   (reqd) — one of: Purchase, Depreciation,
                            Revaluation, Maintenance, Transfer, Disposal,
                            Verification, Split, Adjustment
          description       Small Text
          user              Link → User
          reference_doctype Link → DocType
          reference_name    Dynamic Link
          value_change      Currency
          (standard Frappe child fields: name, parent, parenttype, parentfield,
           idx, creation, modified, modified_by, owner, docstatus)

        WHY raw SQL:
          Child table insert via frappe.get_doc().insert() triggers full parent
          validation, causing docstatus conflicts and recursion during on_cancel.
          Raw SQL inserts cleanly without touching the parent document.

        WHY no docstatus guard:
          on_submit (docstatus=1) and on_cancel (docstatus=2) must both log.
          The old "!= 1" guard silently blocked cancel logs — now removed.
        """
        if not self.name:
            return

        # Map action string to nearest valid transaction_type if not provided
        if not transaction_type:
            action_map = {
                "Submitted": "Purchase",
                "Capitalization": "Purchase",
                "Opening Entry": "Purchase",
                "Depreciation Posted": "Depreciation",
                "Schedule Created": "Depreciation",
                "Recalculation": "Depreciation",
                "Catch-up Depreciation": "Depreciation",
                "Status Change": "Adjustment",
                "Modified": "Adjustment",
                "QR Code": "Verification",
                "Split": "Split",
                "Cancelled": "Disposal",
                "Cancellation": "Disposal",
            }
            transaction_type = action_map.get(action, "Adjustment")

        try:
            now = now_datetime()
            today_date = getdate(nowdate())
            frappe.db.sql("""
                INSERT INTO `tabAsset History Log`
                (name, parent, parenttype, parentfield, idx,
                 transaction_date, `date`, action, transaction_type,
                 description, `user`,
                 reference_doctype, reference_name, value_change,
                 creation, modified, modified_by, owner, docstatus)
                VALUES
                (%(name)s, %(parent)s, 'Fixed Asset', 'asset_history_log', 1,
                 %(transaction_date)s, %(date)s, %(action)s, %(transaction_type)s,
                 %(description)s, %(user)s,
                 %(reference_doctype)s, %(reference_name)s, %(value_change)s,
                 %(now)s, %(now)s, %(user)s, %(user)s, 1)
            """, {
                "name": frappe.generate_hash(length=10),
                "parent": self.name,
                "transaction_date": today_date,
                "date": now,
                "action": action,
                "transaction_type": transaction_type,
                "description": description,
                "user": frappe.session.user,
                "reference_doctype": reference_doctype,
                "reference_name": reference_name,
                "value_change": flt(value_change) if value_change else None,
                "now": now,
            })
            frappe.db.commit()
        except Exception:
            # Never let history logging crash the main operation
            pass


# ============================================================================
# WHITELISTED METHODS FOR CLIENT-SIDE CALLS
# ============================================================================

@frappe.whitelist()
def get_asset_history(asset_name):
    """
    Return history log rows for a Fixed Asset.
    Must be a server-side method because Asset History Log is a child table —
    frappe.client.get_list() cannot query child doctypes directly.
    """
    rows = frappe.db.sql("""
        SELECT
            transaction_date, action, transaction_type,
            description, `user`
        FROM `tabAsset History Log`
        WHERE parent = %s AND parenttype = 'Fixed Asset'
        ORDER BY transaction_date DESC, creation DESC
        LIMIT 100
    """, asset_name, as_dict=True)
    return rows


@frappe.whitelist()
def regenerate_qr_code(asset_name):
    """Force-regenerate QR code for a submitted asset (e.g. if blank on submit)"""
    try:
        asset = frappe.get_doc("Fixed Asset", asset_name)
        if asset.docstatus != 1:
            frappe.throw(_("Asset must be submitted to generate a QR Code"))
        # Clear existing so generate_qr_code() doesn't skip
        asset.qr_code_image = None
        asset.qr_code = None
        asset.generate_qr_code()
        frappe.msgprint(_("QR Code regenerated successfully"), indicator="green", alert=True)
        return {"success": True}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Regenerate QR Code Failed")
        frappe.throw(_("Failed to regenerate QR Code: {0}").format(str(e)))


@frappe.whitelist()
def get_asset_details(asset):
    """Return key asset fields for use in linked doctypes"""
    if not asset:
        return {}

    try:
        d = frappe.get_doc("Fixed Asset", asset)
        return {
            "asset_name": d.asset_name,
            "asset_code": d.asset_code,
            "asset_category": d.asset_category,
            "current_location": d.current_location,
            "custodian": d.custodian,
            "cost_center": d.cost_center,
            "department": d.department,
            "current_net_book_value": d.current_net_book_value,
            "current_gross_value": d.current_gross_value,
            "current_accumulated_depreciation": d.current_accumulated_depreciation,
            "gross_purchase_amount": d.gross_purchase_amount,
            "purchase_date": d.purchase_date,
            "asset_status": d.asset_status,
            "asset_account": d.asset_account,
            "accumulated_depreciation_account": d.accumulated_depreciation_account,
            "depreciation_expense_account": d.depreciation_expense_account,
            "serial_number": d.serial_number,
            "manufacturer": d.manufacturer,
            "model_number": d.model_number,
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Asset Details Failed")
        frappe.throw(_("Failed to get asset details: {0}").format(str(e)))


@frappe.whitelist()
def scan_qr_code(qr_data):
    """Process a scanned QR code payload and return matching asset info"""
    try:
        data = json.loads(qr_data)
        asset_code = data.get("asset_code")

        if not asset_code:
            return {"success": False, "message": _("Invalid QR Code - Asset Code not found")}

        assets = frappe.get_all(
            "Fixed Asset",
            filters={"asset_code": asset_code},
            fields=["name", "asset_name", "asset_code", "current_location",
                    "asset_status", "custodian", "department",
                    "current_net_book_value", "asset_image"]
        )

        if not assets:
            return {"success": False,
                    "message": _("Asset {0} not found in system").format(asset_code)}

        a = assets[0]
        return {
            "success": True,
            "asset": {
                "name": a.name,
                "asset_code": a.asset_code,
                "asset_name": a.asset_name,
                "status": a.asset_status,
                "location": a.current_location,
                "custodian": a.custodian,
                "department": a.department,
                "current_value": a.current_net_book_value,
                "image": a.asset_image,
                "url": f"{frappe.utils.get_url()}/app/fixed-asset/{a.name}"
            }
        }

    except json.JSONDecodeError:
        return {"success": False, "message": _("Invalid QR Code format")}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "QR Code Scan Error")
        return {"success": False, "message": _("Error scanning QR code: {0}").format(str(e))}


@frappe.whitelist()
def generate_depreciation_schedule(asset_name):
    """
    Generate (or regenerate) the depreciation schedule for a submitted asset.
    Called from the JS '📅 Generate Schedule' button.
    """
    try:
        asset = frappe.get_doc("Fixed Asset", asset_name)

        if asset.docstatus != 1:
            frappe.throw(_("Asset must be submitted to generate a depreciation schedule"))

        if not asset.calculate_depreciation:
            frappe.throw(_("Depreciation is not enabled for this asset"))

        # Recalculate values first to ensure schedule uses latest parameters
        asset.calculate_depreciation_values()
        asset.calculate_current_value()

        # Persist recalculated values
        for field in ["depreciable_amount", "total_number_of_depreciations",
                      "total_depreciation_months", "depreciation_rate",
                      "useful_life_months", "salvage_value", "residual_value"]:
            val = getattr(asset, field, None)
            if val is not None:
                asset.db_set(field, val, update_modified=False)

        asset.create_depreciation_schedule()

        return {"success": True, "message": "Schedule generated successfully"}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Generate Depreciation Schedule Failed")
        frappe.throw(_("Failed to generate schedule: {0}").format(str(e)))


@frappe.whitelist()
def recalculate_depreciation(asset_name):
    """
    Recalculate depreciation values only.
    Schedule regeneration must be done separately via '📅 Generate Schedule'.
    """
    try:
        asset = frappe.get_doc("Fixed Asset", asset_name)

        if asset.docstatus != 1:
            frappe.throw(_("Asset must be submitted to recalculate depreciation"))

        if not asset.calculate_depreciation:
            frappe.throw(_("Depreciation is not enabled for this asset"))

        asset.calculate_depreciation_values()
        asset.calculate_current_value()
        asset.update_depreciation_percentage()

        for field in ["depreciable_amount", "total_number_of_depreciations",
                      "total_depreciation_months", "depreciation_rate",
                      "current_accumulated_depreciation", "current_net_book_value",
                      "depreciation_percentage_complete", "useful_life_months"]:
            val = getattr(asset, field, None)
            if val is not None:
                asset.db_set(field, val, update_modified=False)

        asset.log_asset_history("Recalculation", "Depreciation values recalculated")

        frappe.msgprint(
            _("Depreciation values recalculated for {0}. "
              "Use '&#128197; Generate Schedule' to regenerate the schedule.").format(
                frappe.bold(asset.asset_code)),
            indicator="blue", alert=True
        )

        return {"success": True}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Depreciation Recalculation Failed")
        frappe.throw(_("Failed to recalculate depreciation: {0}").format(str(e)))


@frappe.whitelist()
def post_depreciation_entry(schedule_name):
    """Post a single depreciation schedule row as a Journal Entry"""
    try:
        schedule = frappe.get_doc("Depreciation Schedule Details", schedule_name)
        asset = frappe.get_doc("Fixed Asset", schedule.parent)

        if schedule.journal_entry:
            frappe.throw(_("Depreciation already posted for this schedule"))

        if getdate(schedule.schedule_date) > getdate(nowdate()):
            frappe.throw(_("Cannot post depreciation for future date {0}").format(
                format_date(schedule.schedule_date)))

        if not asset.depreciation_expense_account:
            frappe.throw(_("Depreciation Expense Account is not set on asset {0}").format(
                asset.asset_code))

        if not asset.accumulated_depreciation_account:
            frappe.throw(_("Accumulated Depreciation Account is not set on asset {0}").format(
                asset.asset_code))

        je = frappe.new_doc("Journal Entry")
        je.voucher_type = "Depreciation Entry"
        je.company = asset.company
        je.posting_date = schedule.schedule_date
        je.user_remark = _("Depreciation Entry for {0} - {1}").format(
            asset.asset_name, format_date(schedule.schedule_date))

        je.append("accounts", {
            "account": asset.depreciation_expense_account,
            "debit_in_account_currency": flt(schedule.depreciation_amount),
            "cost_center": asset.cost_center,
        })
        je.append("accounts", {
            "account": asset.accumulated_depreciation_account,
            "credit_in_account_currency": flt(schedule.depreciation_amount),
            "cost_center": asset.cost_center,
        })

        je.flags.ignore_permissions = True
        je.insert()
        je.submit()

        # Update schedule row: link JE and set status to Posted
        frappe.db.sql("""
            UPDATE `tabDepreciation Schedule Details`
            SET journal_entry = %s, status = 'Posted'
            WHERE name = %s
        """, (je.name, schedule_name))

        # Refresh asset computed fields
        asset.reload()
        asset.calculate_current_value()
        asset.update_depreciation_percentage()
        asset.db_set("current_accumulated_depreciation",
                     asset.current_accumulated_depreciation, update_modified=False)
        asset.db_set("current_net_book_value",
                     asset.current_net_book_value, update_modified=False)
        asset.db_set("last_depreciation_date",
                     schedule.schedule_date, update_modified=False)
        asset.db_set("depreciation_percentage_complete",
                     asset.depreciation_percentage_complete, update_modified=False)

        next_schedule = frappe.db.get_value(
            "Depreciation Schedule Details",
            {
                "parent": asset.name,
                "parenttype": "Fixed Asset",
                "schedule_date": [">", schedule.schedule_date],
                "journal_entry": ["in", ["", None]]
            },
            "schedule_date",
            order_by="schedule_date asc"
        )
        asset.db_set("next_depreciation_date", next_schedule or None, update_modified=False)

        if flt(asset.current_net_book_value) <= flt(asset.salvage_value or 0):
            asset.update_asset_status("Fully Depreciated")

        asset.log_asset_history(
            "Depreciation Posted",
            f"Depreciation entry {je.name} posted for {format_date(schedule.schedule_date)}",
            "Journal Entry", je.name
        )

        frappe.msgprint(
            _("Depreciation Entry {0} posted successfully").format(
                frappe.get_desk_link("Journal Entry", je.name)),
            indicator="green", alert=True
        )

        return je.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Post Depreciation Failed")
        frappe.throw(_("Failed to post depreciation: {0}").format(str(e)))


@frappe.whitelist()
def bulk_post_depreciation(filters=None):
    """Post all due (past-date, unposted) depreciation schedules"""
    if isinstance(filters, str):
        filters = json.loads(filters) if filters else {}

    due_schedules = frappe.get_all(
        "Depreciation Schedule Details",
        filters={
            "schedule_date": ["<=", nowdate()],
            "journal_entry": ["in", ["", None]],
            "parenttype": "Fixed Asset",
            "status": "Scheduled"
        },
        fields=["name", "parent", "schedule_date", "depreciation_amount"]
    )

    if not due_schedules:
        frappe.msgprint(_("No due depreciation schedules found"), indicator="blue")
        return {"success": True, "posted": 0, "errors": []}

    posted = 0
    errors = []

    for schedule in due_schedules:
        try:
            post_depreciation_entry(schedule.name)
            posted += 1
            frappe.db.commit()
        except Exception as e:
            errors.append(f"{schedule.parent}: {str(e)}")
            frappe.db.rollback()
            frappe.log_error(
                frappe.get_traceback(), f"Bulk Depreciation Failed - {schedule.name}"
            )

    message = _("Posted {0} depreciation entries successfully").format(posted)
    if errors:
        message += f"<br><br><b>Errors ({len(errors)}):</b><br>" + "<br>".join(errors[:10])

    frappe.msgprint(message, indicator="green" if posted > 0 else "orange", alert=True)
    return {"success": True, "posted": posted, "errors": errors}


# ============================================================================
# CATCH-UP DEPRECIATION — POST OUTSTANDING PAST-DUE SCHEDULES
# ============================================================================

@frappe.whitelist()
def get_outstanding_depreciation_schedules(asset_name, up_to_date=None):
    """
    Return all unposted depreciation schedules up to a given date.
    Used by the JS dialog to preview catch-up entries before posting.
    """
    if not up_to_date:
        up_to_date = nowdate()

    asset = frappe.get_doc("Fixed Asset", asset_name)

    if asset.docstatus != 1:
        frappe.throw(_("Asset must be submitted to view outstanding depreciation schedules"))

    if not asset.calculate_depreciation:
        frappe.throw(_("Depreciation is not enabled for this asset"))

    schedules = frappe.get_all(
        "Depreciation Schedule Details",
        filters={
            "parent": asset_name,
            "parenttype": "Fixed Asset",
            "schedule_date": ["<=", getdate(up_to_date)],
            "journal_entry": ["in", ["", None]],
            "status": "Scheduled"
        },
        fields=["name", "schedule_date", "depreciation_amount",
                "accumulated_depreciation", "closing_balance", "opening_balance"],
        order_by="schedule_date asc",
    )

    total_amount = sum(flt(s.depreciation_amount) for s in schedules)

    return {
        "schedules": schedules,
        "total_amount": flt(total_amount, 2),
        "count": len(schedules),
        "asset_name": asset.asset_name,
        "asset_code": asset.asset_code,
        "up_to_date": up_to_date,
        "depreciation_expense_account": asset.depreciation_expense_account,
        "accumulated_depreciation_account": asset.accumulated_depreciation_account,
        "cost_center": asset.cost_center,
        "company": asset.company,
    }


@frappe.whitelist()
def post_catchup_depreciation(asset_name, up_to_date=None, post_as="individual"):
    """
    Post all outstanding (past-due, unposted) depreciation schedules for one asset.

    Args:
        asset_name : Name of the Fixed Asset
        up_to_date : Post schedules on or before this date (default: today)
        post_as    : 'individual' — one JE per period
                     'consolidated' — one combined JE for all periods
    """
    if isinstance(up_to_date, str) and not up_to_date:
        up_to_date = None
    if not up_to_date:
        up_to_date = nowdate()

    asset = frappe.get_doc("Fixed Asset", asset_name)

    if asset.docstatus != 1:
        frappe.throw(_("Asset must be submitted to post depreciation"))

    if not asset.calculate_depreciation:
        frappe.throw(_("Depreciation is not enabled for this asset"))

    schedules = frappe.get_all(
        "Depreciation Schedule Details",
        filters={
            "parent": asset_name,
            "parenttype": "Fixed Asset",
            "schedule_date": ["<=", getdate(up_to_date)],
            "journal_entry": ["in", ["", None]],
            "status": "Scheduled"
        },
        fields=["name", "schedule_date", "depreciation_amount",
                "accumulated_depreciation", "closing_balance"],
        order_by="schedule_date asc",
    )

    if not schedules:
        frappe.msgprint(
            _("No outstanding depreciation schedules found for {0} up to {1}").format(
                frappe.bold(asset.asset_code), format_date(up_to_date)),
            indicator="blue", alert=True,
        )
        return {"success": True, "posted": 0, "journal_entries": []}

    posted_jes = []
    errors = []

    if post_as == "consolidated":
        total_amount = sum(flt(s.depreciation_amount) for s in schedules)
        first_date = schedules[0].schedule_date
        last_date = schedules[-1].schedule_date
        period_label = (
            format_date(first_date) if first_date == last_date
            else f"{format_date(first_date)} to {format_date(last_date)}"
        )

        try:
            je = frappe.new_doc("Journal Entry")
            je.voucher_type = "Depreciation Entry"
            je.company = asset.company
            je.posting_date = last_date
            je.user_remark = _(
                "Catch-up Depreciation for {0} [{1}] - Periods: {2}"
            ).format(asset.asset_name, asset.asset_code, period_label)

            je.append("accounts", {
                "account": asset.depreciation_expense_account,
                "debit_in_account_currency": flt(total_amount, 2),
                "cost_center": asset.cost_center,
                "user_remark": f"Consolidated catch-up - {period_label}",
            })
            je.append("accounts", {
                "account": asset.accumulated_depreciation_account,
                "credit_in_account_currency": flt(total_amount, 2),
                "cost_center": asset.cost_center,
                "user_remark": f"Consolidated catch-up - {period_label}",
            })

            je.flags.ignore_permissions = True
            je.insert()
            je.submit()

            # Link all schedules to this single JE and mark Posted
            for s in schedules:
                frappe.db.sql("""
                    UPDATE `tabDepreciation Schedule Details`
                    SET journal_entry = %s, status = 'Posted'
                    WHERE name = %s
                """, (je.name, s.name))

            posted_jes.append(je.name)

            asset.log_asset_history(
                "Catch-up Depreciation",
                f"Consolidated catch-up JE {je.name} posted for "
                f"{len(schedules)} periods ({period_label})",
                "Journal Entry", je.name,
            )

            frappe.msgprint(
                _("Consolidated catch-up depreciation entry {0} posted for "
                  "{1} periods totalling {2}").format(
                    frappe.get_desk_link("Journal Entry", je.name),
                    len(schedules),
                    frappe.bold(frappe.format_value(total_amount, {"fieldtype": "Currency"})),
                ),
                indicator="green", alert=True,
            )

        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(), f"Consolidated Catch-up Failed - {asset_name}"
            )
            frappe.throw(_("Failed to post consolidated catch-up entry: {0}").format(str(e)))

    else:
        # One JE per period
        for s in schedules:
            try:
                je = frappe.new_doc("Journal Entry")
                je.voucher_type = "Depreciation Entry"
                je.company = asset.company
                je.posting_date = s.schedule_date
                je.user_remark = _(
                    "Catch-up Depreciation for {0} [{1}] - Period: {2}"
                ).format(asset.asset_name, asset.asset_code, format_date(s.schedule_date))

                je.append("accounts", {
                    "account": asset.depreciation_expense_account,
                    "debit_in_account_currency": flt(s.depreciation_amount, 2),
                    "cost_center": asset.cost_center,
                })
                je.append("accounts", {
                    "account": asset.accumulated_depreciation_account,
                    "credit_in_account_currency": flt(s.depreciation_amount, 2),
                    "cost_center": asset.cost_center,
                })

                je.flags.ignore_permissions = True
                je.insert()
                je.submit()

                frappe.db.sql("""
                    UPDATE `tabDepreciation Schedule Details`
                    SET journal_entry = %s, status = 'Posted'
                    WHERE name = %s
                """, (je.name, s.name))

                posted_jes.append(je.name)
                frappe.db.commit()

                asset.log_asset_history(
                    "Catch-up Depreciation",
                    f"Catch-up JE {je.name} posted for period {format_date(s.schedule_date)}",
                    "Journal Entry", je.name,
                )

            except Exception as e:
                errors.append(f"Period {format_date(s.schedule_date)}: {str(e)}")
                frappe.db.rollback()
                frappe.log_error(
                    frappe.get_traceback(), f"Catch-up Failed - {asset_name} / {s.name}"
                )

        msg = _("Posted {0} of {1} catch-up depreciation entries for {2}").format(
            len(posted_jes), len(schedules), frappe.bold(asset.asset_code)
        )
        if errors:
            msg += "<br><br><b>&#9888; Errors:</b><br>" + "<br>".join(errors)

        frappe.msgprint(msg, indicator="green" if not errors else "orange", alert=True)

    # Refresh asset computed values
    asset.reload()
    asset.calculate_current_value()
    asset.update_depreciation_percentage()
    asset.db_set("current_accumulated_depreciation",
                 asset.current_accumulated_depreciation, update_modified=False)
    asset.db_set("current_net_book_value",
                 asset.current_net_book_value, update_modified=False)
    asset.db_set("depreciation_percentage_complete",
                 asset.depreciation_percentage_complete, update_modified=False)
    asset.db_set("last_depreciation_date",
                 schedules[-1].schedule_date if schedules else None, update_modified=False)

    next_pending = frappe.db.get_value(
        "Depreciation Schedule Details",
        {
            "parent": asset.name,
            "parenttype": "Fixed Asset",
            "journal_entry": ["in", ["", None]],
            "status": "Scheduled"
        },
        "schedule_date",
        order_by="schedule_date asc",
    )
    asset.db_set("next_depreciation_date", next_pending or None, update_modified=False)

    if flt(asset.current_net_book_value) <= flt(asset.salvage_value or 0):
        asset.update_asset_status("Fully Depreciated")

    return {
        "success": True,
        "posted": len(posted_jes),
        "errors": errors,
        "journal_entries": posted_jes,
    }


@frappe.whitelist()
def bulk_post_catchup_depreciation(filters=None, up_to_date=None, post_as="individual"):
    """
    Bulk catch-up: post outstanding past-due schedules across all
    submitted, depreciable assets (optionally filtered).
    """
    if isinstance(filters, str):
        filters = json.loads(filters) if filters else {}
    if not filters:
        filters = {}
    if not up_to_date:
        up_to_date = nowdate()

    asset_filters = {"docstatus": 1, "calculate_depreciation": 1}
    asset_filters.update(filters)

    assets = frappe.get_all(
        "Fixed Asset",
        filters=asset_filters,
        fields=["name", "asset_code", "asset_name"],
    )

    if not assets:
        frappe.msgprint(_("No eligible assets found"), indicator="blue")
        return {"success": True, "total_posted": 0, "asset_results": []}

    total_posted = 0
    asset_results = []
    global_errors = []

    for asset_row in assets:
        try:
            result = post_catchup_depreciation(
                asset_name=asset_row.name,
                up_to_date=up_to_date,
                post_as=post_as,
            )
            posted = result.get("posted", 0)
            total_posted += posted
            if posted:
                asset_results.append({
                    "asset": asset_row.asset_code,
                    "asset_name": asset_row.asset_name,
                    "posted": posted,
                    "journal_entries": result.get("journal_entries", []),
                })
        except Exception as e:
            err_msg = f"{asset_row.asset_code} ({asset_row.asset_name}): {str(e)}"
            global_errors.append(err_msg)
            frappe.log_error(
                frappe.get_traceback(), f"Bulk Catch-up Failed - {asset_row.name}"
            )

    msg = _("<b>Bulk Catch-up Depreciation Complete</b><br>")
    msg += _("Assets processed: {0}<br>").format(len(asset_results))
    msg += _("Total journal entries posted: {0}<br>").format(total_posted)
    msg += _("Up to date: {0}").format(format_date(up_to_date))

    if global_errors:
        msg += "<br><br><b>&#9888; Errors ({0}):</b><br>".format(len(global_errors))
        msg += "<br>".join(global_errors[:15])
        if len(global_errors) > 15:
            msg += f"<br>... and {len(global_errors) - 15} more. Check Error Log for details."

    frappe.msgprint(
        msg,
        indicator="green" if not global_errors else "orange",
        title=_("Bulk Catch-up Complete"),
    )

    return {
        "success": True,
        "total_posted": total_posted,
        "asset_results": asset_results,
        "errors": global_errors,
    }

# Add this method to your existing FixedAsset class in fixed_asset.py

@frappe.whitelist()
def get_dashboard_metrics(self):
    """Return comprehensive metrics for the HTML dashboard"""
    try:
        # Asset values
        gross_purchase = flt(self.gross_purchase_amount)
        current_gross = flt(self.current_gross_value or self.gross_purchase_amount)
        salvage = flt(self.salvage_value or 0)
        accumulated_dep = flt(self.current_accumulated_depreciation or 0)
        opening_dep = flt(self.opening_accumulated_depreciation or 0)
        net_book = flt(self.current_net_book_value or 0)
        depreciable = flt(self.depreciable_amount or 0)
        
        # Calculate value metrics
        total_depreciation_posted = accumulated_dep + opening_dep
        depreciation_percentage = (total_depreciation_posted / gross_purchase * 100) if gross_purchase else 0
        remaining_value = gross_purchase - total_depreciation_posted
        value_preserved = (net_book / gross_purchase * 100) if gross_purchase else 0
        
        # Depreciation schedule metrics
        schedules = frappe.get_all('Depreciation Schedule Details',
            filters={'parent': self.name},
            fields=['name', 'schedule_date', 'depreciation_amount', 'status', 'journal_entry'],
            order_by='schedule_date'
        )
        
        total_periods = len(schedules)
        posted_periods = len([s for s in schedules if s.journal_entry])
        pending_periods = total_periods - posted_periods
        
        # Calculate total expected depreciation
        total_expected_depreciation = sum(flt(s.depreciation_amount) for s in schedules)
        total_posted_depreciation = sum(flt(s.depreciation_amount) for s in schedules if s.journal_entry)
        
        # Upcoming schedules
        upcoming = [s for s in schedules if not s.journal_entry and getdate(s.schedule_date) >= getdate(today())]
        overdue = [s for s in schedules if not s.journal_entry and getdate(s.schedule_date) < getdate(today())]
        
        next_depreciation = upcoming[0].schedule_date if upcoming else None
        next_depreciation_amount = flt(upcoming[0].depreciation_amount) if upcoming else 0
        
        # Asset age calculation
        purchase_date = getdate(self.purchase_date) if self.purchase_date else None
        asset_age_months = 0
        if purchase_date:
            today_date = getdate(today())
            asset_age_months = (today_date.year - purchase_date.year) * 12 + (today_date.month - purchase_date.month)
        
        # Useful life metrics
        useful_life = cint(self.useful_life_months or 0)
        remaining_useful_life = useful_life - asset_age_months if useful_life else 0
        life_consumed_pct = (asset_age_months / useful_life * 100) if useful_life else 0
        
        # Maintenance metrics
        maintenance_count = frappe.db.count('Asset Maintenance', 
            filters={'asset': self.name, 'docstatus': 1})
        
        # Insurance status
        insurance_expired = False
        insurance_days = 0
        if self.insurance_expiry_date:
            insurance_days = frappe.utils.date_diff(self.insurance_expiry_date, today())
            insurance_expired = insurance_days < 0
        
        # Warranty status
        warranty_expired = False
        warranty_days = 0
        if self.warranty_expiry_date:
            warranty_days = frappe.utils.date_diff(self.warranty_expiry_date, today())
            warranty_expired = warranty_days < 0
        
        return {
            'asset_code': self.asset_code or 'N/A',
            'asset_name': self.asset_name or 'N/A',
            'asset_status': self.asset_status or 'Draft',
            'asset_category': self.asset_category or 'N/A',
            'company': self.company or 'N/A',
            'department': self.department or 'N/A',
            'current_location': self.current_location or 'N/A',
            'custodian': self.custodian or 'N/A',
            
            # Financial metrics
            'gross_purchase_amount': gross_purchase,
            'current_gross_value': current_gross,
            'salvage_value': salvage,
            'depreciable_amount': depreciable,
            'total_depreciation_posted': total_depreciation_posted,
            'current_net_book_value': net_book,
            'remaining_value': remaining_value,
            'depreciation_percentage': round(depreciation_percentage, 1),
            'value_preserved': round(value_preserved, 1),
            
            # Schedule metrics
            'total_schedule_periods': total_periods,
            'posted_periods': posted_periods,
            'pending_periods': pending_periods,
            'total_expected_depreciation': total_expected_depreciation,
            'total_posted_depreciation': total_posted_depreciation,
            'upcoming_count': len(upcoming),
            'overdue_count': len(overdue),
            'next_depreciation_date': next_depreciation,
            'next_depreciation_amount': next_depreciation_amount,
            
            # Depreciation info
            'is_depreciable': self.is_depreciable_asset or 0,
            'calculate_depreciation': self.calculate_depreciation or 0,
            'depreciation_method': self.depreciation_method or 'N/A',
            'depreciation_frequency': self.depreciation_frequency or 'N/A',
            'depreciation_rate': flt(self.depreciation_rate or 0),
            'depreciation_percentage_complete': flt(self.depreciation_percentage_complete or 0),
            
            # Age & Lifecycle
            'purchase_date': str(self.purchase_date) if self.purchase_date else None,
            'available_for_use_date': str(self.available_for_use_date) if self.available_for_use_date else None,
            'asset_age_months': asset_age_months,
            'useful_life_months': useful_life,
            'remaining_useful_life': remaining_useful_life,
            'life_consumed_pct': round(life_consumed_pct, 1),
            
            # Maintenance & Insurance
            'maintenance_count': maintenance_count,
            'warranty_expiry_date': str(self.warranty_expiry_date) if self.warranty_expiry_date else None,
            'insurance_expiry_date': str(self.insurance_expiry_date) if self.insurance_expiry_date else None,
            'insurance_expired': insurance_expired,
            'insurance_days': insurance_days,
            'warranty_expired': warranty_expired,
            'warranty_days': warranty_days,
            
            # Additional flags
            'is_existing_asset': self.is_existing_asset or 0,
            'has_qr_code': bool(self.qr_code_image),
            'asset_quantity': cint(self.asset_quantity or 1),
        }
    except Exception as e:
        frappe.log_error(f"Dashboard metrics error: {str(e)}", "Asset Dashboard")
        return {}