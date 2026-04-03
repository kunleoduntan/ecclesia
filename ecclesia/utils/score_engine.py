import frappe


RATING_BANDS = [
    (4.5, "Outstanding"),
    (3.5, "Exceeds Expectations"),
    (2.5, "Meets Expectations"),
    (1.5, "Needs Improvement"),
    (0.0, "Unsatisfactory"),
]


def compute_composite_score(record_name: str) -> dict:
    rec   = frappe.get_doc("Employee Performance Record", record_name)
    cycle = frappe.get_doc("Performance Cycle", rec.cycle)

    kpi_score              = _kpi_score(rec)
    self_score             = _self_score(rec)
    peer_score, peer_count = _peer_score(rec)
    manager_score          = _manager_score(rec)

    w = {
        "kpi":     (cycle.kpi_weight     or 40) / 100,
        "manager": (cycle.manager_weight or 35) / 100,
        "peer":    (cycle.peer_weight    or 15) / 100,
        "self":    (cycle.self_weight    or 10) / 100,
    }

    composite = (
        kpi_score     * w["kpi"]     +
        manager_score * w["manager"] +
        peer_score    * w["peer"]    +
        self_score    * w["self"]
    )

    final_rating = map_to_rating(composite, cycle)

    frappe.db.set_value("Employee Performance Record", record_name, {
        "kpi_score":         round(kpi_score, 2),
        "self_score":        round(self_score, 2),
        "peer_score":        round(peer_score, 2),
        "peer_review_count": peer_count,
        "manager_score":     round(manager_score, 2),
        "composite_score":   round(composite, 2),
        "final_rating":      final_rating,
    })
    frappe.db.commit()

    return {
        "kpi_score":       round(kpi_score, 2),
        "self_score":      round(self_score, 2),
        "peer_score":      round(peer_score, 2),
        "manager_score":   round(manager_score, 2),
        "composite_score": round(composite, 2),
        "final_rating":    final_rating,
    }


def map_to_rating(score: float, cycle=None) -> str:
    if cycle and getattr(cycle, "rating_scale", None):
        for row in sorted(cycle.rating_scale, key=lambda r: r.min_score, reverse=True):
            if score >= row.min_score:
                return row.rating_label
    for threshold, label in RATING_BANDS:
        if score >= threshold:
            return label
    return "Unsatisfactory"


def _kpi_score(rec) -> float:
    if not rec.goals:
        return 0.0
    total_weight = sum(g.weight or 0 for g in rec.goals) or 1
    weighted_sum = 0.0
    for g in rec.goals:
        if g.actual_value and g.target_value:
            try:
                pct = (float(g.actual_value) / float(g.target_value)) * 100
                pct = min(pct, 120)
                if   pct >= 120: score = 5.0
                elif pct >= 100: score = 4.0 + (pct - 100) / 20
                elif pct >= 80:  score = 3.0 + (pct - 80)  / 20
                elif pct >= 60:  score = 2.0 + (pct - 60)  / 20
                else:            score = max(1.0, pct / 60)
            except (ValueError, ZeroDivisionError):
                score = float(g.self_score or 0)
        else:
            score = float(g.self_score or 0)
        weighted_sum += score * ((g.weight or 0) / total_weight)
    return min(weighted_sum, 5.0)


def _self_score(rec) -> float:
    scores = [float(g.self_score) for g in rec.goals if g.self_score]
    return sum(scores) / len(scores) if scores else 0.0


def _peer_score(rec) -> tuple:
    rows = frappe.db.sql("""
        SELECT rr.rating
        FROM   `tabReview Response` rr
        JOIN   `tabPeer Review Request` prr ON prr.name = rr.parent
        WHERE  prr.reviewee = %s AND prr.cycle = %s
          AND  prr.status   = 'Completed' AND rr.rating IS NOT NULL
    """, (rec.employee, rec.cycle), as_dict=True)

    count = frappe.db.count("Peer Review Request", {
        "reviewee": rec.employee, "cycle": rec.cycle, "status": "Completed"
    })
    ratings = [float(r.rating) for r in rows if r.rating]
    return (sum(ratings) / len(ratings) if ratings else 0.0), count


def _manager_score(rec) -> float:
    mgr = frappe.db.get_value(
        "Manager Review",
        {"performance_record": rec.name, "status": "Submitted"},
        ["name", "overall_score"], as_dict=True
    )
    if not mgr:
        return 0.0

    goal_scores = frappe.db.sql("""
        SELECT manager_score FROM `tabManager Goal Comment`
        WHERE  parent = %s AND manager_score IS NOT NULL AND manager_score != ''
    """, mgr.name, as_dict=True)

    if goal_scores:
        avg = sum(float(r.manager_score) for r in goal_scores) / len(goal_scores)
        return round(float(mgr.overall_score or 0) * 0.6 + avg * 0.4, 2)
    return float(mgr.overall_score or 0)