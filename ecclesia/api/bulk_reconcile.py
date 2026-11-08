# apps/ecclesia/ecclesia/api/bulk_reconcile.py
import frappe
from frappe.utils import now
from erpnext.accounts.party import get_party_account

PPR = "Process Payment Reconciliation"
PARTY_TYPES = ("Customer", "Supplier")

COMPANY_ADVANCE_FIELD = {
    "Customer": "default_advance_received_account",
    "Supplier": "default_advance_paid_account",
}


def get_candidates(company=None):
    cond = "AND company = %(company)s" if company else ""
    return frappe.db.sql(
        f"""
        SELECT company, party_type, party, account
        FROM `tabPayment Ledger Entry`
        WHERE delinked = 0 AND party_type IN %(pt)s {cond}
        GROUP BY company, party_type, party, account
        HAVING ABS(SUM(amount)) > 0.005
        """,
        {"pt": PARTY_TYPES, "company": company},
        as_dict=True,
    )


def get_advance_account(company, party_type, party):
    """Version-aware. Returns None when this version has no advance-account field
    (or it is optional and nothing is configured). Never substitutes another
    account: a wrong advance account can misclassify advances."""
    fld = frappe.get_meta(PPR).get_field("default_advance_account")
    if not fld:
        return None

    acc = None
    if frappe.get_meta("Party Account").has_field("advance_account"):
        acc = frappe.db.get_value(
            "Party Account",
            {"parenttype": party_type, "parent": party, "company": company},
            "advance_account",
        )
    acc = acc or frappe.get_cached_value("Company", company, COMPANY_ADVANCE_FIELD[party_type])

    if not acc and fld.reqd:
        frappe.throw(
            f"No advance account for {party_type} {party}. Set "
            f"'{COMPANY_ADVANCE_FIELD[party_type]}' on Company {company} "
            f"(or the advance account on the {party_type}'s Accounts table)."
        )
    return acc


def run(company=None, party_type=None):
    started = now()
    created, skipped, failed = 0, 0, []

    for c in get_candidates(company):
        if party_type and c.party_type != party_type:
            continue
        try:
            if frappe.db.exists(
                PPR,
                {
                    "company": c.company,
                    "party_type": c.party_type,
                    "party": c.party,
                    "docstatus": 1,
                    "status": ["in", ["Queued", "Running", "Paused"]],
                },
            ):
                skipped += 1
                continue

            values = {
                "doctype": PPR,
                "company": c.company,
                "party_type": c.party_type,
                "party": c.party,
                "receivable_payable_account": c.account
                or get_party_account(c.party_type, c.party, c.company),
            }
            adv = get_advance_account(c.company, c.party_type, c.party)
            if adv:
                values["default_advance_account"] = adv

            doc = frappe.get_doc(values)
            doc.insert()
            doc.submit()
            frappe.db.commit()
            created += 1
        except Exception as e:
            frappe.db.rollback()
            failed.append((c.party_type, c.party, str(e)[:200]))
            frappe.log_error(frappe.get_traceback(), f"Bulk PPR: {c.party_type} {c.party}")

    return {"started": started, "created": created, "skipped": skipped, "failed": failed}


# ───────────── SAFETY TOOLS ─────────────

def cancel_queued(company=None):
    """Cancel submitted records that have not started processing."""
    filters = {"docstatus": 1, "status": "Queued"}
    if company:
        filters["company"] = company
    done = []
    for name in frappe.get_all(PPR, filters=filters, pluck="name"):
        frappe.get_doc(PPR, name).cancel()
        done.append(name)
    frappe.db.commit()
    return done


def balances(company):
    """Net GL balance (debit - credit) of every advance and payable/receivable
    account in use. Run before and after processing and compare."""
    accounts = set()
    for f in COMPANY_ADVANCE_FIELD.values():
        a = frappe.get_cached_value("Company", company, f)
        if a:
            accounts.add(a)
    accounts.update(
        frappe.db.sql_list(
            "SELECT DISTINCT account FROM `tabPayment Ledger Entry` WHERE company=%s AND delinked=0",
            company,
        )
    )
    if not accounts:
        return {}
    rows = frappe.db.sql(
        """SELECT account, SUM(debit - credit) AS bal FROM `tabGL Entry`
           WHERE company=%s AND is_cancelled=0 AND account IN %s GROUP BY account""",
        (company, tuple(accounts)),
        as_dict=True,
    )
    return {r.account: r.bal for r in rows}


def new_gl_since(since, company=None):
    """GL rows created since a timestamp, grouped by voucher type and account.
    Shows exactly what reconciliation posted, if anything."""
    cond = "AND company = %(company)s" if company else ""
    return frappe.db.sql(
        f"""SELECT voucher_type, account, COUNT(*) AS rows_,
                   SUM(debit) AS debit, SUM(credit) AS credit
            FROM `tabGL Entry`
            WHERE creation >= %(since)s AND is_cancelled = 0 {cond}
            GROUP BY voucher_type, account""",
        {"since": since, "company": company},
        as_dict=True,
    )


@frappe.whitelist()
def run_bulk(company=None, party_type=None):
    frappe.only_for(["Accounts Manager", "System Manager"])
    frappe.enqueue(run, queue="long", timeout=3600, company=company, party_type=party_type)