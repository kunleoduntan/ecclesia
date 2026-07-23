"""
ecclesia/api/performance_portal.py
====================================
360° Performance Management API — all @frappe.whitelist() methods
Place at: ecclesia/ecclesia/api/performance_portal.py

Methods:
  get_portal_context       — bootstrap data on page load
  get_goals                — employee goals list
  create_goal              — create + submit for approval
  update_goal_progress     — update % and milestone
  get_self_appraisal       — fetch existing or blank
  save_self_appraisal      — save draft or submit
  get_my_peer_reviews_received
  submit_peer_review
  save_manager_review
  compute_composite_score
  get_idp
  update_idp_activity
  send_feedback
  get_feedback_timeline
  get_calibration_data
  override_calibrated_rating
  get_ai_coaching          — Claude AI career coach
  screen_resume            — AI resume scoring
  get_shortlisted_candidates
  get_analytics
"""
import frappe
from frappe import _
from frappe.utils import nowdate, flt, cint, add_days, date_diff
import json


# ── HELPERS ───────────────────────────────────────────────

def _get_employee(user=None):
    user = user or frappe.session.user
    emp = frappe.db.get_value("Employee",
        {"user_id": user, "status": "Active"}, "name")
    if not emp:
        frappe.throw(_("No active Employee linked to your account."))
    return emp


def _safe(val):
    return val.isoformat() if hasattr(val, "isoformat") else val


def _emp_dict(employee=None):
    employee = employee or _get_employee()
    row = frappe.db.get_value("Employee", employee,
        ["name","employee_name","designation","department","branch","reports_to"],
        as_dict=True)
    return {k: _safe(v) for k, v in (row or {}).items()}


def _update_perf_record(employee, cycle, updates):
    existing = frappe.db.get_value("Employee Performance Record",
        {"employee": employee, "cycle": cycle}, "name")
    if existing:
        frappe.db.set_value("Employee Performance Record", existing, updates)
    else:
        doc = frappe.new_doc("Employee Performance Record")
        doc.employee = employee
        doc.cycle = cycle
        for k, v in updates.items():
            doc.set(k, v)
        doc.insert(ignore_permissions=True)
    frappe.db.commit()


def _get_active_cycle():
    return frappe.db.get_value("Performance Cycle", {"status": "Active"}, "name")


# ── BOOTSTRAP ─────────────────────────────────────────────

@frappe.whitelist()
def get_portal_context():
    employee = _get_employee()
    emp = _emp_dict(employee)

    cycle_name = _get_active_cycle()
    cycle = None
    if cycle_name:
        cycle = frappe.db.get_value("Performance Cycle", cycle_name,
            ["name","title","cycle_type","end_date","start_date"],
            as_dict=True)
        cycle = {k: _safe(v) for k, v in cycle.items()}

    record = frappe.db.get_value("Employee Performance Record",
        {"employee": employee},
        ["name","cycle","composite_score","final_rating","status"],
        order_by="creation desc", as_dict=True)
    if record:
        record = {k: _safe(v) for k, v in record.items()}

    days_left = None
    if cycle and cycle.get("end_date"):
        days_left = date_diff(cycle["end_date"], nowdate())

    pending = {}
    if cycle_name:
        has_self = frappe.db.exists("Self Appraisal",
            {"employee": employee, "performance_cycle": cycle_name,
             "status": ["!=", "Draft"]})
        pending["self_appraisal"] = not bool(has_self)

    return {
        "employee": emp,
        "cycle": cycle,
        "performance_record": record,
        "pending": pending,
        "days_left": days_left,
    }


# ── GOALS ─────────────────────────────────────────────────

@frappe.whitelist()
def get_goals(cycle=None):
    employee = _get_employee()
    filters = {"owner_employee": employee}
    if cycle:
        filters["performance_cycle"] = cycle
    goals = frappe.get_all("Performance Goal", filters=filters,
        fields=["name","goal_title","goal_type","category","weight","priority",
                "target_value","current_achievement","progress","due_date",
                "status","description","kpi","measurement_unit"],
        order_by="priority, due_date")
    return [{k: _safe(v) for k, v in g.items()} for g in goals]


@frappe.whitelist()
def create_goal(goal_title, goal_type, category, weight, priority,
                target_value, measurement_unit, due_date,
                description=None, kpi=None, aligned_to=None, cycle=None):
    employee = _get_employee()
    doc = frappe.new_doc("Performance Goal")
    doc.owner_employee = employee
    doc.goal_title = goal_title
    doc.goal_type = goal_type
    doc.category = category
    doc.weight = flt(weight)
    doc.priority = priority
    doc.target_value = target_value
    doc.measurement_unit = measurement_unit
    doc.due_date = due_date
    doc.description = description
    doc.kpi = kpi
    doc.aligned_to_goal = aligned_to
    doc.status = "Pending Approval"
    doc.performance_cycle = cycle or _get_active_cycle()
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    # Notify manager
    mgr = frappe.db.get_value("Employee", employee, "reports_to")
    if mgr:
        mgr_user = frappe.db.get_value("Employee", mgr, "user_id")
        if mgr_user:
            frappe.sendmail(recipients=[mgr_user],
                subject=f"New Goal for Approval: {goal_title}",
                message=f"{_emp_dict(employee).get('employee_name')} submitted goal '{goal_title}' for approval.")
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def update_goal_progress(goal_name, progress, notes=None):
    employee = _get_employee()
    doc = frappe.get_doc("Performance Goal", goal_name)
    if doc.owner_employee != employee:
        frappe.throw(_("Access denied"))
    doc.progress = cint(progress)
    if notes:
        doc.add_comment("Comment", notes)
    if cint(progress) >= 100:
        doc.status = "Completed"
    elif doc.status == "Not Started":
        doc.status = "In Progress"
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "status": doc.status}


# ── SELF APPRAISAL ────────────────────────────────────────

@frappe.whitelist()
def get_self_appraisal(cycle=None):
    employee = _get_employee()
    cycle = cycle or _get_active_cycle()
    existing = frappe.db.get_value("Self Appraisal",
        {"employee": employee, "performance_cycle": cycle},
        ["name","status","goal_self_score","overall_self_rating",
         "goal_summary","key_accomplishments","challenges","lessons_learned",
         "training_completed","strengths","improvement_areas",
         "improvement_plan","overall_comments","ai_feedback"],
        as_dict=True)
    if existing:
        return {k: _safe(v) for k, v in existing.items()}
    return {"exists": False, "cycle": cycle}


@frappe.whitelist()
def save_self_appraisal(data, submit=False):
    if isinstance(data, str):
        data = json.loads(data)
    employee = _get_employee()
    cycle = data.get("performance_cycle") or _get_active_cycle()
    existing = frappe.db.get_value("Self Appraisal",
        {"employee": employee, "performance_cycle": cycle}, "name")
    if existing:
        doc = frappe.get_doc("Self Appraisal", existing)
    else:
        doc = frappe.new_doc("Self Appraisal")
        doc.employee = employee
        doc.performance_cycle = cycle
        doc.submission_date = nowdate()
    allowed = ["goal_summary","goal_self_score","key_accomplishments",
               "challenges","lessons_learned","training_completed",
               "future_aspirations","strengths","improvement_areas",
               "improvement_plan","overall_comments","overall_self_rating"]
    for field in allowed:
        if field in data:
            doc.set(field, data[field])
    doc.status = "Submitted" if submit else "Draft"
    doc.save(ignore_permissions=True)
    if submit:
        _update_perf_record(employee, cycle,
            {"self_score": flt(data.get("overall_self_rating")),
             "self_appraisal_date": nowdate()})
        frappe.enqueue("ecclesia.api.performance_portal._generate_ai_feedback",
            appraisal=doc.name, queue="short", timeout=120)
    frappe.db.commit()
    return {"success": True, "name": doc.name, "status": doc.status}


def _generate_ai_feedback(appraisal):
    """Background: generate Claude AI coaching feedback on self appraisal."""
    try:
        import requests
        doc = frappe.get_doc("Self Appraisal", appraisal)
        prompt = (
            "You are an HR coach. Read this self-appraisal and provide:\n"
            "1. Three specific strengths observed\n"
            "2. Two constructive development suggestions\n"
            "3. One motivational sentence\n\n"
            f"Accomplishments: {doc.key_accomplishments}\n"
            f"Challenges: {doc.challenges}\n"
            f"Strengths: {doc.strengths}\n"
            f"Improvement Areas: {doc.improvement_areas}\n"
            f"Self Rating: {doc.overall_self_rating}/5\n\n"
            "Tone: warm, professional. Max 250 words."
        )
        resp = requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30)
        if resp.ok:
            text = resp.json().get("content", [{}])[0].get("text", "")
            if text:
                frappe.db.set_value("Self Appraisal", appraisal, "ai_feedback", text)
                frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Self Appraisal Feedback Error")


# ── PEER REVIEW ───────────────────────────────────────────

@frappe.whitelist()
def get_my_peer_reviews_received(cycle=None):
    employee = _get_employee()
    filters = {"reviewee": employee, "status": "Submitted"}
    if cycle:
        filters["performance_cycle"] = cycle
    reviews = frappe.get_all("Peer Review", filters=filters,
        fields=["name","overall_peer_rating","overall_recommendation",
                "strengths","improvement_suggestions","overall_comments",
                "is_anonymous","reviewer","submission_date"])
    result = []
    for r in reviews:
        r = {k: _safe(v) for k, v in r.items()}
        if r.get("is_anonymous"):
            r["reviewer_name"] = "Anonymous"
        else:
            r["reviewer_name"] = frappe.db.get_value(
                "Employee", r["reviewer"], "employee_name") or ""
        result.append(r)
    return result


@frappe.whitelist()
def submit_peer_review(reviewee, request_name, data):
    if isinstance(data, str):
        data = json.loads(data)
    reviewer = _get_employee()
    cycle = frappe.db.get_value("Peer Review Request", request_name, "performance_cycle")
    doc = frappe.new_doc("Peer Review")
    doc.reviewer = reviewer
    doc.reviewee = reviewee
    doc.peer_review_request = request_name
    doc.performance_cycle = cycle
    doc.submission_date = nowdate()
    doc.is_anonymous = cint(data.get("is_anonymous", 1))
    for field in ["collaboration_feedback","communication_feedback","leadership_feedback",
                  "innovation_feedback","strengths","improvement_suggestions",
                  "overall_recommendation","overall_comments","overall_peer_rating"]:
        if field in data:
            doc.set(field, data[field])
    for row in data.get("competency_ratings", []):
        doc.append("competency_ratings", row)
    doc.status = "Submitted"
    doc.insert(ignore_permissions=True)
    # Mark peer as done in request
    req = frappe.get_doc("Peer Review Request", request_name)
    for peer_row in req.peers:
        if peer_row.peer == reviewer:
            peer_row.status = "Completed"
            peer_row.review_name = doc.name
            break
    req.save(ignore_permissions=True)
    # Recalculate peer average
    reviews = frappe.get_all("Peer Review",
        filters={"reviewee": reviewee, "performance_cycle": cycle, "status": "Submitted"},
        fields=["overall_peer_rating"])
    if reviews:
        avg = sum(flt(r.overall_peer_rating) for r in reviews) / len(reviews)
        _update_perf_record(reviewee, cycle, {"peer_score": round(avg, 2)})
    frappe.db.commit()
    return {"success": True, "name": doc.name}


# ── MANAGER REVIEW ────────────────────────────────────────

@frappe.whitelist()
def save_manager_review(employee, data):
    if isinstance(data, str):
        data = json.loads(data)
    manager = _get_employee()
    cycle = data.get("performance_cycle") or _get_active_cycle()
    existing = frappe.db.get_value("Manager Review 360",
        {"employee": employee, "performance_cycle": cycle}, "name")
    if existing:
        doc = frappe.get_doc("Manager Review 360", existing)
    else:
        doc = frappe.new_doc("Manager Review 360")
        doc.employee = employee
        doc.manager = manager
        doc.performance_cycle = cycle
        doc.review_date = nowdate()
    for field in ["goal_score","competency_score","values_score","overall_manager_rating",
                  "goal_assessment","overall_comments","strengths_observed","development_needs",
                  "recommend_promotion","recommend_increment","increment_percentage",
                  "recommend_bonus","bonus_amount","recommend_training","training_details",
                  "recommend_pip","pip_reason","recommend_transfer",
                  "recommend_succession","succession_role"]:
        if field in data:
            doc.set(field, data[field])
    doc.status = "Submitted" if data.get("submit") else "Draft"
    doc.save(ignore_permissions=True)
    if data.get("submit"):
        _update_perf_record(employee, cycle, {
            "manager_score": flt(data.get("overall_manager_rating")),
            "manager_review_date": nowdate()})
        if data.get("recommend_pip"):
            frappe.enqueue("ecclesia.api.performance_portal._auto_create_pip",
                employee=employee, reason=data.get("pip_reason",""),
                queue="short")
    frappe.db.commit()
    return {"success": True, "name": doc.name, "status": doc.status}


def _auto_create_pip(employee, reason=""):
    if not frappe.db.exists("DocType", "Performance PIP"):
        return
    if frappe.db.exists("Performance PIP",
            {"employee": employee, "status": ["not in",["Passed","Failed","Cancelled"]]}):
        return
    emp = frappe.get_doc("Employee", employee)
    doc = frappe.new_doc("Performance PIP")
    doc.employee = employee
    doc.manager = emp.reports_to
    doc.start_date = nowdate()
    doc.end_date = add_days(nowdate(), 90)
    doc.reason_for_pip = reason or "Recommended by manager review"
    doc.status = "Active"
    doc.insert(ignore_permissions=True)
    frappe.db.commit()


# ── COMPOSITE SCORE ───────────────────────────────────────

@frappe.whitelist()
def compute_composite_score(employee=None, cycle=None):
    employee = employee or _get_employee()
    cycle = cycle or _get_active_cycle()
    config = frappe.db.get_value("Performance Weight Config",
        {"performance_cycle": cycle},
        ["goal_weight","self_weight","peer_weight","manager_weight"],
        as_dict=True) or {"goal_weight":50,"self_weight":20,"peer_weight":20,"manager_weight":60}
    record = frappe.db.get_value("Employee Performance Record",
        {"employee": employee, "cycle": cycle},
        ["self_score","peer_score","manager_score"], as_dict=True) or {}
    # Reviewer weighted average
    rw = flt(config["self_weight"]) + flt(config["peer_weight"]) + flt(config["manager_weight"]) or 100
    reviewer_score = (
        flt(record.get("self_score")) * flt(config["self_weight"]) +
        flt(record.get("peer_score")) * flt(config["peer_weight"]) +
        flt(record.get("manager_score")) * flt(config["manager_weight"])
    ) / rw
    # Goal score from Progress Goal table
    goals = frappe.get_all("Performance Goal",
        filters={"owner_employee": employee, "performance_cycle": cycle},
        fields=["weight","progress"])
    tw = sum(flt(g.weight) for g in goals) or 1
    goal_score = sum((flt(g.weight)/tw) * flt(g.progress) for g in goals)
    gw = flt(config["goal_weight"]) / 100
    composite = (goal_score/100 * gw + reviewer_score/5 * (1-gw)) * 100
    _update_perf_record(employee, cycle, {
        "kpi_score": round(goal_score,1),
        "composite_score": round(composite,1)})
    frappe.db.commit()
    return {"composite_score": round(composite,1), "goal_score": round(goal_score,1)}


# ── IDP ───────────────────────────────────────────────────

@frappe.whitelist()
def get_idp():
    employee = _get_employee()
    idp = frappe.db.get_value("Performance IDP",
        {"employee": employee, "status": ["in",["Active","Draft"]]},
        ["name","plan_period","career_goal","overall_progress",
         "mentor","manager_support","status","review_date"],
        order_by="creation desc", as_dict=True)
    if not idp:
        return {"exists": False}
    idp = {k: _safe(v) for k, v in idp.items()}
    items = frappe.get_all("IDP Item", filters={"parent": idp["name"]},
        fields=["name","activity","activity_type","target_completion","status","progress","notes"])
    idp["items"] = [{k: _safe(v) for k, v in it.items()} for it in items]
    return idp


@frappe.whitelist()
def update_idp_activity(idp_name, row_name, progress, status=None, notes=None):
    employee = _get_employee()
    idp = frappe.get_doc("Performance IDP", idp_name)
    if idp.employee != employee:
        frappe.throw(_("Access denied"))
    for row in idp.idp_items:
        if row.name == row_name:
            row.progress = cint(progress)
            if status:
                row.status = status
            if notes:
                row.notes = notes
            break
    progs = [flt(r.progress) for r in idp.idp_items]
    idp.overall_progress = round(sum(progs) / max(1, len(progs)), 1)
    idp.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True, "overall_progress": idp.overall_progress}


# ── CONTINUOUS FEEDBACK ───────────────────────────────────

@frappe.whitelist()
def send_feedback(to_employee, feedback_type, feedback, visibility, cycle=None):
    from_employee = _get_employee()
    doc = frappe.new_doc("Continuous Feedback")
    doc.from_employee = from_employee
    doc.to_employee = to_employee
    doc.feedback_type = feedback_type
    doc.feedback = feedback
    doc.visibility = visibility
    doc.feedback_date = nowdate()
    doc.performance_cycle = cycle
    doc.is_acknowledged = 0
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    recipient_user = frappe.db.get_value("Employee", to_employee, "user_id")
    if recipient_user:
        sender_name = frappe.db.get_value("Employee", from_employee, "employee_name")
        frappe.sendmail(recipients=[recipient_user],
            subject=f"New {feedback_type} from {sender_name}",
            message=f"You received {feedback_type} feedback:<br><br>{feedback}")
    return {"success": True, "name": doc.name}


@frappe.whitelist()
def get_feedback_timeline(limit=20):
    employee = _get_employee()
    rows = frappe.get_all("Continuous Feedback",
        filters={"to_employee": employee},
        fields=["name","from_employee","feedback_type","feedback",
                "feedback_date","visibility","is_acknowledged"],
        order_by="feedback_date desc", limit=cint(limit))
    result = []
    for r in rows:
        r = {k: _safe(v) for k, v in r.items()}
        r["from_name"] = frappe.db.get_value("Employee", r["from_employee"], "employee_name") or ""
        result.append(r)
    return result


# ── CALIBRATION ───────────────────────────────────────────

@frappe.whitelist()
def get_calibration_data(cycle=None, department=None):
    cycle = cycle or _get_active_cycle()
    filters = {"cycle": cycle, "status": ["!=","Cancelled"]}
    if department:
        emps = [e.name for e in frappe.get_all("Employee",
            filters={"department": department}, fields=["name"])]
        if emps:
            filters["employee"] = ["in", emps]
    records = frappe.get_all("Employee Performance Record", filters=filters,
        fields=["name","employee","composite_score","final_rating",
                "calibrated_rating","kpi_score","peer_score","manager_score","self_score"])
    dist = {"1":[],"2":[],"3":[],"4":[],"5":[]}
    for r in records:
        score = flt(r.get("calibrated_rating") or r.get("composite_score") or 0)
        bucket = str(min(5, max(1, round(score/20))))
        dist[bucket].append({
            "employee": r["employee"],
            "name": frappe.db.get_value("Employee", r["employee"], "employee_name"),
            "score": score
        })
    avg = sum(flt(r.get("composite_score",0)) for r in records) / max(1, len(records))
    return {"records": records, "distribution": dist, "average": round(avg,2), "total": len(records)}


@frappe.whitelist()
def override_calibrated_rating(employee, calibrated_rating, override_reason,
                                session_name=None, cycle=None):
    frappe.only_for("HR Manager")
    cycle = cycle or _get_active_cycle()
    original = frappe.db.get_value("Employee Performance Record",
        {"employee": employee, "cycle": cycle}, "composite_score")
    _update_perf_record(employee, cycle, {
        "calibrated_rating": flt(calibrated_rating),
        "calibration_notes": override_reason,
        "calibration_status": "Calibrated",
    })
    if session_name:
        session = frappe.get_doc("HR Calibration Session", session_name)
        session.append("overrides", {
            "employee": employee,
            "original_rating": original,
            "calibrated_rating": flt(calibrated_rating),
            "override_reason": override_reason,
            "approved_by": _get_employee(),
        })
        session.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


# ── AI COACHING ───────────────────────────────────────────

@frappe.whitelist()
def get_ai_coaching(message):
    """Call Claude AI with employee performance context as the coach."""
    employee = _get_employee()
    emp = _emp_dict(employee)
    cycle = _get_active_cycle()
    record = frappe.db.get_value("Employee Performance Record",
        {"employee": employee, "cycle": cycle},
        ["composite_score","kpi_score","self_score","peer_score","manager_score"],
        as_dict=True) or {}
    goals = frappe.get_all("Performance Goal",
        filters={"owner_employee": employee, "performance_cycle": cycle},
        fields=["goal_title","progress","status"], limit=8)

    context = (
        "You are an empathetic HR performance coach embedded in the Ecclesia HR platform.\n\n"
        f"Employee: {emp.get('employee_name')}, {emp.get('designation')}, {emp.get('department')}\n"
        f"Composite Score: {flt(record.get('composite_score',87))}%\n"
        f"Goal Score: {flt(record.get('kpi_score',90))}%\n"
        f"Peer Score: {flt(record.get('peer_score',84))}%\n"
        f"Self Score: {flt(record.get('self_score',80))}%\n"
        f"Manager Score: {flt(record.get('manager_score',0))}%\n\n"
        "Goals:\n" +
        "\n".join(f"- {g['goal_title']}: {g['progress']}% ({g['status']})" for g in goals) +
        f"\n\nEmployee question: {message}\n\n"
        "Respond as a warm coach. Be specific to this employee's data. "
        "Max 300 words. Use bullet points for key actions."
    )
    try:
        import requests
        resp = requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 500,
                  "messages": [{"role": "user", "content": context}]},
            timeout=25)
        if resp.ok:
            text = resp.json().get("content",[{}])[0].get("text","")
            if text:
                return {"response": text, "source": "claude"}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Coaching Error")
    return {"response": (
        f"Based on your data, you're performing at an estimated "
        f"{flt(record.get('composite_score',87)):.0f}% composite score — strong work. "
        f"For '{message}': focus on documenting your achievements with specific numbers "
        f"and linking them to department goals. Would you like tips on any specific area?"
    ), "source": "fallback"}


# ── RESUME SELECTION ──────────────────────────────────────

@frappe.whitelist()
def screen_resume(resume_name, job_opening=None):
    """AI-powered resume screening against Job Requirement Profile."""
    frappe.only_for("HR Manager")
    resume = frappe.get_doc("Resume", resume_name)
    job_opening = job_opening or resume.job_opening
    profile = frappe.db.get_value("Job Requirement Profile",
        {"job_opening": job_opening},
        ["name","min_experience_years","min_education","required_certifications",
         "auto_shortlist_threshold","auto_reject_threshold",
         "education_weight","experience_weight","skills_weight","certifications_weight"],
        as_dict=True)
    if not profile:
        frappe.throw(f"No Job Requirement Profile found for {job_opening}. Please create one first.")

    req_skills = frappe.get_all("Job Requirement Skill",
        filters={"parent": profile.name}, fields=["skill","is_mandatory","weight"])

    prompt = (
        "You are a professional HR recruiter. Analyse this resume against the requirements.\n"
        "Return ONLY a JSON object (no markdown, no explanation):\n"
        '{"education_score":0-100,"experience_score":0-100,"skills_score":0-100,'
        '"certifications_score":0-100,"matched_skills":[""],'
        '"missing_mandatory_skills":[""],"knockout_failed":true/false,'
        '"ai_recommendation":"Strong Hire|Hire|Maybe|No Hire","ai_narrative":"2-3 sentences"}\n\n'
        f"Job Requirements:\n"
        f"- Min Experience: {profile.min_experience_years} years\n"
        f"- Min Education: {profile.min_education}\n"
        f"- Required Skills: {', '.join(s['skill'] for s in req_skills)}\n"
        f"- Mandatory Skills: {', '.join(s['skill'] for s in req_skills if s.get('is_mandatory'))}\n"
        f"- Certifications: {profile.required_certifications}\n\n"
        f"Candidate:\n"
        f"- Experience: {resume.parsed_years_experience} years\n"
        f"- Education: {resume.parsed_education}\n"
        f"- Skills: {resume.parsed_skills}\n"
        f"- Certifications: {resume.parsed_certifications}\n"
        f"- Resume Text: {(resume.parsed_raw_text or '')[:2000]}"
    )

    scores = {"education_score":70,"experience_score":70,"skills_score":70,
              "certifications_score":65,"matched_skills":[],"missing_mandatory_skills":[],
              "knockout_failed":False,"ai_recommendation":"Maybe",
              "ai_narrative":"AI scoring unavailable. Manual review required."}
    try:
        import requests
        resp = requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30)
        if resp.ok:
            raw = resp.json().get("content",[{}])[0].get("text","").strip().strip("```json").strip("```")
            scores = json.loads(raw)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Resume AI Screening Error")

    ew = flt(profile.education_weight)/100
    xw = flt(profile.experience_weight)/100
    sw = flt(profile.skills_weight)/100
    cw = flt(profile.certifications_weight)/100
    tw = ew + xw + sw + cw or 1
    total = (flt(scores.get("education_score"))*ew + flt(scores.get("experience_score"))*xw +
             flt(scores.get("skills_score"))*sw + flt(scores.get("certifications_score"))*cw) / tw

    tsl = flt(profile.auto_shortlist_threshold) or 70
    tar = flt(profile.auto_reject_threshold) or 40
    if scores.get("knockout_failed"):
        decision = "Rejected"
    elif total >= tsl:
        decision = "Shortlisted"
    elif total < tar:
        decision = "Rejected"
    else:
        decision = "Refer to HR"

    result = frappe.new_doc("Resume Screening Result")
    result.resume = resume_name
    result.job_opening = job_opening
    result.screening_date = nowdate()
    result.education_score = flt(scores.get("education_score"))
    result.experience_score = flt(scores.get("experience_score"))
    result.skills_score = flt(scores.get("skills_score"))
    result.certifications_score = flt(scores.get("certifications_score"))
    result.total_score = round(total, 1)
    result.matched_skills = ", ".join(scores.get("matched_skills",[]))
    result.missing_mandatory_skills = ", ".join(scores.get("missing_mandatory_skills",[]))
    result.knockout_failed = cint(scores.get("knockout_failed",0))
    result.auto_decision = decision
    result.ai_narrative = scores.get("ai_narrative","")
    result.insert(ignore_permissions=True)
    frappe.db.set_value("Resume", resume_name, {
        "status": "Shortlisted" if decision=="Shortlisted" else
                  "Rejected" if decision=="Rejected" else "Parsed",
        "ai_summary": scores.get("ai_narrative",""),
        "ai_recommendation": scores.get("ai_recommendation",""),
    })
    frappe.db.commit()
    return {"total_score": round(total,1), "auto_decision": decision,
            "scores": scores, "result_name": result.name}


@frappe.whitelist()
def get_shortlisted_candidates(job_opening):
    results = frappe.get_all("Resume Screening Result",
        filters={"job_opening": job_opening, "auto_decision": ["in",["Shortlisted","Refer to HR"]]},
        fields=["name","resume","total_score","ai_narrative","auto_decision",
                "hr_override","matched_skills","missing_mandatory_skills","screening_date"],
        order_by="total_score desc")
    enriched = []
    for r in results:
        r = {k: _safe(v) for k, v in r.items()}
        res = frappe.db.get_value("Resume", r["resume"],
            ["candidate_name","ai_recommendation","parsed_education",
             "parsed_years_experience","parsed_skills"], as_dict=True) or {}
        r.update({k: _safe(v) for k, v in res.items()})
        enriched.append(r)
    return enriched


# ── ANALYTICS ─────────────────────────────────────────────

@frappe.whitelist()
def get_analytics(cycle=None):
    frappe.only_for(["HR Manager","System Manager"])
    cycle = cycle or _get_active_cycle()
    total = frappe.db.count("Employee", {"status": "Active"})
    completed = frappe.db.count("Employee Performance Record",
        {"cycle": cycle, "status": ["in",["Final","Released"]]})
    dept_avgs = frappe.db.sql("""
        SELECT e.department, COUNT(*) AS cnt, AVG(r.composite_score) AS avg_score
        FROM `tabEmployee Performance Record` r
        JOIN `tabEmployee` e ON e.name = r.employee
        WHERE r.cycle = %s AND r.docstatus != 2
        GROUP BY e.department ORDER BY avg_score DESC LIMIT 10
    """, cycle, as_dict=True)
    pip_count = frappe.db.count("Performance PIP", {"status":"Active"}) \
        if frappe.db.exists("DocType","Performance PIP") else 0
    return {
        "cycle": cycle,
        "total_employees": total,
        "completed": completed,
        "completion_pct": round(completed/max(1,total)*100, 1),
        "dept_averages": dept_avgs,
        "active_pips": pip_count,
    }