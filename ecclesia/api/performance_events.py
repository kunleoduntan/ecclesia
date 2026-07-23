"""
ecclesia/api/performance_events.py
====================================
Module-level event handler functions registered in hooks.py doc_events.

KEY RULE IN FRAPPE:
  - Class methods (validate, before_save, on_submit, after_insert, on_update)
    on a DocType controller fire AUTOMATICALLY. Do NOT register them in hooks.py.
  - hooks.py doc_events are for CROSS-MODULE listeners that need to run
    when DocType A is saved and it should trigger logic in Module B.
  - Every function here has signature: def fn(doc, method=None)

Place at: ecclesia/ecclesia/api/performance_events.py
"""

import frappe
from frappe.utils import flt, nowdate


# ── Goal updated → refresh EPR goal score ────────────────────────────

def on_goal_update(doc, method=None):
    """
    When a Performance Goal is saved/updated, recalculate the KPI
    score on the Employee Performance Record for that cycle.
    Only runs when status is Approved or higher and progress > 0.
    """
    if not (doc.owner_employee and doc.performance_cycle):
        return
    if doc.status in ("Draft", "Pending Approval", "Cancelled"):
        return

    _refresh_epr_kpi_score(doc.owner_employee, doc.performance_cycle)


def _refresh_epr_kpi_score(employee, cycle):
    """
    Recalculate the weighted KPI score for an employee in a cycle
    from all their approved/completed goals.
    Weighted average of goal progress × goal weight.
    """
    goals = frappe.get_all("Performance Goal",
        filters={
            "owner_employee":    employee,
            "performance_cycle": cycle,
            "status":            ["in", ["Approved", "In Progress", "Completed"]],
        },
        fields=["progress", "weight"])

    if not goals:
        return

    total_weight    = sum(flt(g.weight) for g in goals)
    weighted_progress = sum(flt(g.progress) * flt(g.weight) for g in goals)

    if total_weight == 0:
        return

    kpi_score = round(weighted_progress / total_weight, 1)

    epr = frappe.db.get_value("Employee Performance Record",
        {"employee": employee, "cycle": cycle}, "name")

    if epr:
        frappe.db.set_value("Employee Performance Record", epr, "kpi_score", kpi_score)
        frappe.db.commit()


# ── Self Appraisal submitted → update EPR self score ─────────────────

def on_self_appraisal_submit(doc, method=None):
    """
    When a Self Appraisal is submitted, copy the overall self rating
    and submission date to the Employee Performance Record.
    """
    if not (doc.employee and doc.performance_cycle):
        return

    epr = frappe.db.get_value("Employee Performance Record",
        {"employee": doc.employee, "cycle": doc.performance_cycle}, "name")

    if epr:
        frappe.db.set_value("Employee Performance Record", epr, {
            "self_score":           flt(doc.overall_self_rating),
            "self_appraisal_date":  nowdate(),
        })
        frappe.db.commit()


# ── Peer Review submitted → update EPR peer average ──────────────────

def on_peer_review_submit(doc, method=None):
    """
    When any Peer Review is submitted, recalculate the average peer score
    across all submitted reviews for that employee in the cycle.
    """
    if not (doc.reviewee and doc.performance_cycle):
        return

    reviews = frappe.get_all("Peer Review",
        filters={
            "reviewee":          doc.reviewee,
            "performance_cycle": doc.performance_cycle,
            "docstatus":         1,
        },
        fields=["overall_peer_rating", "name"])

    if not reviews:
        return

    ratings = [flt(r.overall_peer_rating) for r in reviews if flt(r.overall_peer_rating) > 0]
    if not ratings:
        return

    avg_peer = round(sum(ratings) / len(ratings), 2)

    epr = frappe.db.get_value("Employee Performance Record",
        {"employee": doc.reviewee, "cycle": doc.performance_cycle}, "name")

    if epr:
        frappe.db.set_value("Employee Performance Record", epr, {
            "peer_score":       avg_peer,
            "peer_review_count": len(reviews),
        })
        frappe.db.commit()


# ── Manager Review submitted → update EPR manager score ──────────────

def on_manager_review_submit(doc, method=None):
    """
    When a Manager Review 360 is submitted, copy the overall manager
    rating to the Employee Performance Record and set review date.
    """
    if not (doc.employee and doc.performance_cycle):
        return

    epr = frappe.db.get_value("Employee Performance Record",
        {"employee": doc.employee, "cycle": doc.performance_cycle}, "name")

    if epr:
        frappe.db.set_value("Employee Performance Record", epr, {
            "manager_score":       flt(doc.overall_manager_rating),
            "manager_review_date": nowdate(),
            "promotion_recommended": doc.recommend_promotion or 0,
            "increment_recommended": doc.recommend_increment or 0,
            "increment_percentage":  flt(doc.increment_percentage),
        })
        frappe.db.commit()


# ── EPR updated → refresh cycle-level analytics ───────────────────────

def on_perf_record_update(doc, method=None):
    """
    When an Employee Performance Record is saved, refresh the
    cycle-level analytics fields (completion_rate, avg_composite_score,
    performance_breakdown) on the parent Performance Cycle document.
    Runs asynchronously so it doesn't slow form saves.
    """
    if not doc.cycle:
        return
    # Only refresh if a meaningful score field changed
    meaningful_fields = {
        "composite_score", "calibrated_rating", "final_rating", "status"
    }
    changed = set(doc.get_doc_before_save() and
                  [f for f in meaningful_fields
                   if doc.get(f) != (doc.get_doc_before_save() or {}).get(f)]
                  or meaningful_fields)   # fallback: always run on first save
    if not changed:
        return

    frappe.enqueue(
        "ecclesia.api.performance_events._refresh_cycle_stats",
        cycle=doc.cycle,
        queue="short",
        timeout=60,
        now=frappe.flags.in_test,
    )


def _refresh_cycle_stats(cycle):
    """Recompute aggregated stats on the Performance Cycle document."""
    try:
        cycle_doc = frappe.get_doc("Performance Cycle", cycle)
        cycle_doc._compute_progress_metrics()
        cycle_doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         f"Cycle Analytics Refresh Error: {cycle}")