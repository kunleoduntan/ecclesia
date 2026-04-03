import frappe
from frappe.utils import get_url


def notify_supervisor_handover(hn_doc):
    sup_user = frappe.db.get_value("Employee", hn_doc.supervisor, "user_id")
    if not sup_user:
        return
    _send(sup_user,
          f"Handover Note awaiting review — {hn_doc.employee_name}",
          f"""<p><strong>{hn_doc.employee_name}</strong> has submitted a Handover Note
              for leave <strong>{hn_doc.leave_from}</strong> to <strong>{hn_doc.leave_to}</strong>.</p>
              {_btn(f'/app/handover-note/{hn_doc.name}', 'Review Handover Note')}""")


def notify_acting_officers(hn_doc):
    officers = {t.acting_officer for t in hn_doc.tasks if t.acting_officer}
    officers.add(hn_doc.default_acting_officer)
    officers.discard(None)
    link = get_url(f"/app/handover-note/{hn_doc.name}")
    for emp in officers:
        user = frappe.db.get_value("Employee", emp, "user_id")
        if not user:
            continue
        tasks = [t for t in hn_doc.tasks
                 if (t.acting_officer or hn_doc.default_acting_officer) == emp]
        task_html = "".join(
            f"<li>[{t.priority}] {t.task_description} — due {t.due_date or 'no date'}</li>"
            for t in tasks
        )
        _send(user,
              f"Acting cover for {hn_doc.employee_name} — {hn_doc.leave_from} to {hn_doc.leave_to}",
              f"""<p>You are acting for <strong>{hn_doc.employee_name}</strong>.</p>
                  <ul>{task_html}</ul>{_btn(link, 'Open Handover Note')}""")


def notify_peer_reviewers(cycle_name, cycle_title):
    pending = frappe.get_all("Peer Review Request",
                             filters={"cycle": cycle_name, "status": "Pending"},
                             fields=["reviewer"], distinct=True)
    for r in pending:
        user = frappe.db.get_value("Employee", r.reviewer, "user_id")
        if user:
            _send(user,
                  f"Peer review requests awaiting you — {cycle_title}",
                  f"""<p>You have pending peer review requests for
                      <strong>{cycle_title}</strong>.</p>
                      {_btn(get_url('/app/peer-review-request?status=Pending'),
                            'Complete your reviews')}""")


def notify_results_released(employee, record_name, cycle_title, composite, rating):
    user = frappe.db.get_value("Employee", employee, "user_id")
    if not user:
        return
    _send(user,
          f"Your performance results are ready — {cycle_title}",
          f"""<p>Your evaluation for <strong>{cycle_title}</strong> is complete.</p>
              <p><strong>Composite Score:</strong> {composite:.2f}<br>
              <strong>Final Rating:</strong> {rating or 'Pending'}</p>
              {_btn(get_url(f'/app/employee-performance-record/{record_name}'),
                    'View your results')}""")


def _send(recipient, subject, body):
    frappe.sendmail(
        recipients=[recipient], subject=subject,
        message=f"""
            <div style="font-family:sans-serif;max-width:600px;padding:24px">
                {body}
                <p style="font-size:12px;color:#888;margin-top:32px">
                    Sent by Ecclesia — Value Impacts Consulting
                </p>
            </div>""",
        now=False
    )


def _btn(url, label):
    return (f'<p><a href="{url}" style="display:inline-block;padding:10px 20px;'
            f'background:#534AB7;color:#fff;border-radius:6px;'
            f'text-decoration:none;font-weight:500">{label}</a></p>')