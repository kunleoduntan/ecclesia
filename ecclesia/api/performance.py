import frappe
from ecclesia.utils.score_engine import compute_composite_score


@frappe.whitelist()
def recompute_all_scores(cycle_name: str):
    records = frappe.get_all("Employee Performance Record",
                             filters={"cycle": cycle_name}, fields=["name"])
    for r in records:
        compute_composite_score(r.name)
    return {"recomputed": len(records)}


@frappe.whitelist()
def get_cycle_completion_stats(cycle: str) -> dict:
    total = frappe.db.count("Employee Performance Record", {"cycle": cycle})
    if not total:
        return {}

    goals_set = frappe.db.sql("""
        SELECT COUNT(DISTINCT epr.name) FROM `tabEmployee Performance Record` epr
        JOIN   `tabPerformance Goal` pg ON pg.parent = epr.name
        WHERE  epr.cycle = %s
    """, cycle)[0][0]

    self_done = frappe.db.count("Employee Performance Record", {
        "cycle": cycle, "self_appraisal_date": ["is", "set"]
    })
    mgr_done = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabManager Review` mr
        JOIN   `tabEmployee Performance Record` epr ON epr.name = mr.performance_record
        WHERE  epr.cycle = %s AND mr.status = 'Submitted'
    """, cycle)[0][0]
    calibrated = frappe.db.count("Employee Performance Record", {
        "cycle": cycle, "calibrated_rating": ["is", "set"]
    })
    peer_done = frappe.db.count("Peer Review Request", {
        "cycle": cycle, "status": "Completed"
    })
    peer_total = frappe.db.count("Peer Review Request", {"cycle": cycle})

    return {
        "total": total, "goals_set": goals_set,
        "self_done": self_done, "mgr_done": mgr_done,
        "calibrated": calibrated, "peer_done": peer_done,
        "peer_total": peer_total,
    }


@frappe.whitelist()
def get_peer_summary_for_manager(performance_record: str):
    rec = frappe.get_doc("Employee Performance Record", performance_record)
    rows = frappe.db.sql("""
        SELECT rr.competency,
               ROUND(AVG(CAST(rr.rating AS FLOAT)), 2) AS avg_rating,
               COUNT(*)                                 AS review_count
        FROM   `tabReview Response` rr
        JOIN   `tabPeer Review Request` prr ON prr.name = rr.parent
        WHERE  prr.reviewee = %s AND prr.cycle = %s
          AND  prr.status   = 'Completed' AND rr.rating IS NOT NULL
        GROUP BY rr.competency ORDER BY avg_rating DESC
    """, (rec.employee, rec.cycle), as_dict=True)
    return [{"competency": r.competency,
             "avg": float(r.avg_rating),
             "count": int(r.review_count)} for r in rows]


@frappe.whitelist()
def get_rating_distribution(cycle: str, department: str = None):
    filters = {"cycle": cycle}
    if department:
        filters["department"] = department
    records = frappe.get_all("Employee Performance Record",
                             filters=filters,
                             fields=["calibrated_rating", "final_rating",
                                     "composite_score", "department",
                                     "employee_name"])
    dist = {}
    for r in records:
        rating = r.calibrated_rating or r.final_rating or "Unrated"
        dist[rating] = dist.get(rating, 0) + 1
    return {"distribution": dist, "records": records, "total": len(records)}


@frappe.whitelist()
def get_nine_box_data(cycle: str, department: str = None):
    filters = {"cycle": cycle}
    if department:
        filters["department"] = department
    records = frappe.get_all("Employee Performance Record",
                             filters=filters,
                             fields=["name", "employee_name", "department",
                                     "kpi_score", "peer_score", "composite_score",
                                     "calibrated_rating", "final_rating"])
    return records


@frappe.whitelist()
def get_team_heatmap(cycle: str):
    """Competency × department heatmap data for HR analytics."""
    rows = frappe.db.sql("""
        SELECT epr.department,
               rr.competency,
               ROUND(AVG(CAST(rr.rating AS FLOAT)), 2) AS avg_score,
               COUNT(*) AS response_count
        FROM   `tabReview Response` rr
        JOIN   `tabPeer Review Request` prr ON prr.name = rr.parent
        JOIN   `tabEmployee Performance Record` epr
               ON epr.employee = prr.reviewee AND epr.cycle = prr.cycle
        WHERE  prr.cycle  = %s
          AND  prr.status = 'Completed'
          AND  rr.rating IS NOT NULL
        GROUP BY epr.department, rr.competency
    """, cycle, as_dict=True)
    return rows