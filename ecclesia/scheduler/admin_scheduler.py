# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/scheduler/admin_scheduler.py
"""
Admin Module Scheduler
═══════════════════════
Daily, weekly, and monthly scheduled jobs for the Admin module.

Registered in hooks.py → scheduler_events:
    "daily":   ["ecclesia.ecclesia.scheduler.admin_scheduler.run_daily"]
    "weekly":  ["ecclesia.ecclesia.scheduler.admin_scheduler.run_weekly"]
    "monthly": ["ecclesia.ecclesia.scheduler.admin_scheduler.run_monthly"]
"""

import frappe
from frappe import _
from frappe.utils import nowdate, add_days, date_diff, flt, getdate


# ══════════════════════════════════════════════════════════════════════════════
#  DAILY
# ══════════════════════════════════════════════════════════════════════════════

def run_daily():
    """
    Runs every day. Jobs:
      1. Update vehicle status for stale "In Use" trips
      2. Flag expiring vehicle documents
      3. Flag expiring service contracts
      4. Flag expiring compliance register items
      5. Auto-update environmental permit status
      6. Auto-update expatriate permit status
      7. Auto-update license management status
    """
    frappe.logger().info("[admin_scheduler] run_daily started")

    _update_stale_vehicle_status()
    _flag_expiring_vehicle_documents()
    _flag_expiring_service_contracts()
    _update_permit_statuses()
    _update_license_statuses()

    frappe.db.commit()
    frappe.logger().info("[admin_scheduler] run_daily complete")


def _update_stale_vehicle_status():
    """
    Safety fallback: if a Vehicle Trip Log was submitted more than 24 hours ago
    and the vehicle is still 'In Use', set it back to 'Available'.
    Handles cases where the trip end was never recorded.
    """
    try:
        cutoff = add_days(nowdate(), -1)
        stale_trips = frappe.db.sql("""
            SELECT DISTINCT vtl.vehicle
            FROM `tabVehicle Trip Log` vtl
            JOIN `tabCompany Vehicle` cv ON cv.name = vtl.vehicle
            WHERE vtl.docstatus = 1
              AND vtl.trip_date <= %s
              AND cv.vehicle_status = 'In Use'
              AND vtl.trip_end_time IS NULL
        """, (cutoff,), as_dict=True)

        for row in stale_trips:
            frappe.db.set_value("Company Vehicle", row.vehicle,
                                "vehicle_status", "Available",
                                update_modified=False)
            frappe.logger().info(
                f"[admin_scheduler] Reset stale vehicle to Available: {row.vehicle}"
            )
    except Exception as e:
        frappe.log_error(f"_update_stale_vehicle_status failed: {e}", "Admin Scheduler")


def _flag_expiring_vehicle_documents():
    """
    Flag vehicles whose insurance, road worthiness, or licence is
    expiring within 30 days. Sets vehicle_doc_expiry_alert = 1.
    """
    try:
        if not frappe.db.has_column("Company Vehicle", "insurance_expiry"):
            return

        today     = getdate(nowdate())
        threshold = add_days(nowdate(), 30)

        vehicles = frappe.db.get_all(
            "Company Vehicle",
            filters={"is_active": 1},
            fields=["name", "plate_number", "insurance_expiry",
                    "road_worthiness_expiry", "vehicle_licence_expiry",
                    "assigned_to"]
        )

        for v in vehicles:
            expiring = []
            for field, label in [
                ("insurance_expiry",        "Insurance"),
                ("road_worthiness_expiry",  "Road Worthiness"),
                ("vehicle_licence_expiry",  "Vehicle Licence"),
            ]:
                expiry = v.get(field)
                if expiry and getdate(expiry) <= getdate(threshold):
                    days = date_diff(expiry, nowdate())
                    expiring.append(f"{label} ({days}d)")

            if expiring and v.get("assigned_to"):
                email = frappe.db.get_value("Employee", v.assigned_to, "company_email")
                if email:
                    frappe.sendmail(
                        recipients=[email],
                        subject=_(f"⚠️ Vehicle Document Expiry Alert: {v.plate_number}"),
                        message=_(
                            "<p>The following documents for vehicle <b>{0}</b> "
                            "are expiring soon:</p><ul>{1}</ul>"
                            "<p><a href='/Form/Company Vehicle/{2}'>View Vehicle →</a></p>"
                        ).format(
                            v.plate_number,
                            "".join(f"<li>{item}</li>" for item in expiring),
                            v.name
                        )
                    )
    except Exception as e:
        frappe.log_error(f"_flag_expiring_vehicle_documents failed: {e}", "Admin Scheduler")


def _flag_expiring_service_contracts():
    """
    Notify responsible officer for service contracts expiring within 60 days.
    """
    try:
        if not frappe.db.table_exists("tabService Contract"):
            return

        threshold = add_days(nowdate(), 60)
        contracts = frappe.db.get_all(
            "Service Contract",
            filters={
                "docstatus": 1,
                "contract_end_date": ["between", [nowdate(), threshold]],
                "status": ["!=", "Expired"]
            },
            fields=["name", "contract_title", "vendor", "contract_end_date",
                    "contract_value", "responsible_officer"]
        )

        for c in contracts:
            days = date_diff(c.contract_end_date, nowdate())
            if not c.responsible_officer:
                continue
            email = frappe.db.get_value("Employee", c.responsible_officer, "company_email")
            if not email:
                continue
            frappe.sendmail(
                recipients=[email],
                subject=_(f"⚠️ Service Contract Expiring in {days} days: {c.contract_title}"),
                message=_(
                    "<p>Service Contract <b>{0}</b> with <b>{1}</b> "
                    "expires on <b>{2}</b> ({3} days remaining).</p>"
                    "<p>Contract Value: ₦{4:,.0f}</p>"
                    "<p><a href='/Form/Service Contract/{5}'>Review Contract →</a></p>"
                ).format(
                    c.contract_title, c.vendor or "—",
                    c.contract_end_date, days,
                    flt(c.contract_value), c.name
                )
            )
    except Exception as e:
        frappe.log_error(f"_flag_expiring_service_contracts failed: {e}", "Admin Scheduler")


def _update_permit_statuses():
    """
    Auto-update status on Expatriate Permit Register based on days to expiry.
    Active → Expiring Soon (≤90d) → Expired.
    """
    try:
        if not frappe.db.table_exists("tabExpatriate Permit Register"):
            return

        today = nowdate()
        soon  = add_days(today, 90)

        # Mark expired
        frappe.db.sql("""
            UPDATE `tabExpatriate Permit Register`
            SET status = 'Expired',
                days_to_expiry = DATEDIFF(expiry_date, CURDATE())
            WHERE expiry_date < %s
              AND status NOT IN ('Cancelled', 'Expired')
        """, (today,))

        # Mark expiring soon
        frappe.db.sql("""
            UPDATE `tabExpatriate Permit Register`
            SET status = 'Expiring Soon',
                days_to_expiry = DATEDIFF(expiry_date, CURDATE())
            WHERE expiry_date BETWEEN %s AND %s
              AND status NOT IN ('Cancelled', 'Expired', 'Renewing')
        """, (today, soon))

        # Refresh days_to_expiry on active ones
        frappe.db.sql("""
            UPDATE `tabExpatriate Permit Register`
            SET days_to_expiry = DATEDIFF(expiry_date, CURDATE())
            WHERE status = 'Active'
        """)

    except Exception as e:
        frappe.log_error(f"_update_permit_statuses failed: {e}", "Admin Scheduler")


def _update_license_statuses():
    """
    Auto-update status on License Management based on days to expiry.
    Only updates records where auto_status_update = 1.
    """
    try:
        if not frappe.db.table_exists("tabLicense Management"):
            return

        today = nowdate()
        soon_30  = add_days(today, 30)
        soon_90  = add_days(today, 90)

        # Mark expired
        frappe.db.sql("""
            UPDATE `tabLicense Management`
            SET status = 'Expired',
                days_to_expiry = DATEDIFF(current_expiry_date, CURDATE())
            WHERE current_expiry_date < %s
              AND auto_status_update = 1
              AND status NOT IN ('Suspended', 'Revoked', 'Expired')
        """, (today,))

        # Mark expiring soon (within 30 days)
        frappe.db.sql("""
            UPDATE `tabLicense Management`
            SET status = 'Expiring Soon',
                days_to_expiry = DATEDIFF(current_expiry_date, CURDATE())
            WHERE current_expiry_date BETWEEN %s AND %s
              AND auto_status_update = 1
              AND status NOT IN ('Suspended', 'Revoked', 'Under Renewal')
        """, (today, soon_30))

        # Refresh days_to_expiry on active ones
        frappe.db.sql("""
            UPDATE `tabLicense Management`
            SET days_to_expiry = DATEDIFF(current_expiry_date, CURDATE())
            WHERE auto_status_update = 1
              AND status = 'Active'
        """)

        # Send alerts for licenses expiring in 90, 30, 7 days
        _send_license_expiry_alerts()

    except Exception as e:
        frappe.log_error(f"_update_license_statuses failed: {e}", "Admin Scheduler")


def _send_license_expiry_alerts():
    """Send expiry alert emails for licenses at 90/30/7 day thresholds."""
    try:
        today = nowdate()
        alert_days = [90, 30, 7]

        for days in alert_days:
            target_date = add_days(today, days)
            licenses = frappe.db.get_all(
                "License Management",
                filters={
                    "current_expiry_date": target_date,
                    "status": ["not in", ["Suspended", "Revoked", "Expired"]],
                    f"alert_{days}_days": 1
                },
                fields=["name", "license_name", "license_type", "company",
                        "current_expiry_date", "assigned_to",
                        "alert_email", "renewal_cost"]
            )

            for lic in licenses:
                recipients = []
                if lic.alert_email:
                    recipients.append(lic.alert_email)
                elif lic.assigned_to:
                    email = frappe.db.get_value("Employee", lic.assigned_to, "company_email")
                    if email:
                        recipients.append(email)

                if not recipients:
                    continue

                from ecclesia.ecclesia.compliance_setup.email_templates import (
                    render_permit_expiry_alert, send_compliance_email
                )
                html = render_permit_expiry_alert(
                    doc_name=lic.name,
                    doc_type="License Management",
                    permit_name=lic.license_name,
                    company=lic.company,
                    expiry_date=lic.current_expiry_date,
                    days_to_expiry=days,
                    responsible_officer=lic.assigned_to,
                    renewal_cost=lic.renewal_cost,
                    renewal_lead_days=90
                )
                send_compliance_email(
                    recipients=recipients,
                    subject=f"⚠️ License Expiry Alert ({days} days): {lic.license_name}",
                    html_body=html
                )
    except Exception as e:
        frappe.log_error(f"_send_license_expiry_alerts failed: {e}", "Admin Scheduler")


# ══════════════════════════════════════════════════════════════════════════════
#  WEEKLY
# ══════════════════════════════════════════════════════════════════════════════

def run_weekly():
    """
    Runs every week. Jobs:
      1. Refresh all vehicle analytics (cost per km, YTD fuel, YTD trips)
      2. Refresh facility KPIs (maintenance cost YTD, utility cost YTD)
    """
    frappe.logger().info("[admin_scheduler] run_weekly started")

    _refresh_vehicle_analytics()
    _refresh_facility_kpis()

    frappe.db.commit()
    frappe.logger().info("[admin_scheduler] run_weekly complete")


def _refresh_vehicle_analytics():
    """Recompute YTD analytics for all active vehicles."""
    try:
        if not frappe.db.table_exists("tabCompany Vehicle"):
            return

        vehicles = frappe.db.get_all(
            "Company Vehicle",
            filters={"is_active": 1},
            pluck="name"
        )

        for vehicle in vehicles:
            try:
                # YTD trip totals
                year = getdate(nowdate()).year
                trips = frappe.db.sql("""
                    SELECT
                        COUNT(*) AS trip_count,
                        COALESCE(SUM(distance_km), 0) AS total_km,
                        COALESCE(SUM(fuel_cost), 0) AS fuel_cost
                    FROM `tabVehicle Trip Log`
                    WHERE vehicle = %s
                      AND docstatus = 1
                      AND YEAR(trip_date) = %s
                """, (vehicle, year), as_dict=True)[0]

                fuel = frappe.db.sql("""
                    SELECT COALESCE(SUM(total_cost), 0) AS fuel_cost
                    FROM `tabFuel Issue`
                    WHERE vehicle = %s
                      AND docstatus = 1
                      AND YEAR(issue_date) = %s
                """, (vehicle, year), as_dict=True)[0]

                total_km   = flt(trips.total_km)
                total_cost = flt(trips.fuel_cost) + flt(fuel.fuel_cost)
                cost_per_km = round(total_cost / total_km, 2) if total_km > 0 else 0

                frappe.db.set_value("Company Vehicle", vehicle, {
                    "trips_ytd":    int(trips.trip_count),
                    "km_ytd":       total_km,
                    "fuel_cost_ytd":total_cost,
                    "cost_per_km":  cost_per_km,
                }, update_modified=False)

            except Exception as ve:
                frappe.log_error(
                    f"Vehicle analytics failed for {vehicle}: {ve}",
                    "Admin Scheduler"
                )
    except Exception as e:
        frappe.log_error(f"_refresh_vehicle_analytics failed: {e}", "Admin Scheduler")


def _refresh_facility_kpis():
    """Recompute YTD maintenance and utility costs for all facilities."""
    try:
        if not frappe.db.table_exists("tabFacility"):
            return

        year = getdate(nowdate()).year
        facilities = frappe.db.get_all("Facility", filters={"status": "Active"}, pluck="name")

        for facility in facilities:
            try:
                # Maintenance cost YTD from Maintenance Work Orders
                maint = frappe.db.sql("""
                    SELECT COALESCE(SUM(total_cost), 0) AS cost
                    FROM `tabMaintenance Work Order`
                    WHERE facility = %s
                      AND docstatus = 1
                      AND YEAR(completion_date) = %s
                """, (facility, year), as_dict=True)
                maint_cost = flt(maint[0].cost) if maint else 0

                # Utility cost YTD from Utility Consumption
                utility = frappe.db.sql("""
                    SELECT COALESCE(SUM(total_bill_amount), 0) AS cost
                    FROM `tabUtility Consumption`
                    WHERE facility = %s
                      AND docstatus = 1
                      AND YEAR(reading_date) = %s
                """, (facility, year), as_dict=True)
                utility_cost = flt(utility[0].cost) if utility else 0

                # Open maintenance requests
                open_requests = frappe.db.count(
                    "Facility Maintenance Request",
                    {"facility": facility, "status": ["not in", ["Completed", "Cancelled"]]}
                )

                frappe.db.set_value("Facility", facility, {
                    "maintenance_cost_ytd":  maint_cost,
                    "utility_cost_ytd":      utility_cost,
                    "open_maintenance_requests": open_requests,
                }, update_modified=False)

            except Exception as fe:
                frappe.log_error(
                    f"Facility KPI refresh failed for {facility}: {fe}",
                    "Admin Scheduler"
                )
    except Exception as e:
        frappe.log_error(f"_refresh_facility_kpis failed: {e}", "Admin Scheduler")


# ══════════════════════════════════════════════════════════════════════════════
#  MONTHLY
# ══════════════════════════════════════════════════════════════════════════════

def run_monthly():
    """
    Runs every month. Jobs:
      1. Alert if no utility reading submitted for active meters this month
      2. Monthly vehicle cost summary email to fleet managers
    """
    frappe.logger().info("[admin_scheduler] run_monthly started")

    _alert_missing_utility_readings()
    _monthly_fleet_summary()

    frappe.db.commit()
    frappe.logger().info("[admin_scheduler] run_monthly complete")


def _alert_missing_utility_readings():
    """
    Flag active utility meters that have no reading submitted this month.
    Notifies the responsible person to submit a reading.
    """
    try:
        if not frappe.db.table_exists("tabUtility Meter"):
            return

        from frappe.utils import get_first_day, get_last_day
        month_start = get_first_day(nowdate())
        month_end   = get_last_day(nowdate())

        meters = frappe.db.get_all(
            "Utility Meter",
            filters={"is_active": 1},
            fields=["name", "meter_name", "meter_type", "facility",
                    "company", "responsible_person"]
        )

        for meter in meters:
            # Check if a reading exists for this month
            has_reading = frappe.db.exists("Utility Consumption", {
                "utility_meter": meter.name,
                "docstatus": 1,
                "reading_date": ["between", [month_start, month_end]]
            })

            if has_reading:
                continue

            if not meter.responsible_person:
                continue

            email = frappe.db.get_value(
                "Employee", meter.responsible_person, "company_email"
            )
            if not email:
                continue

            frappe.sendmail(
                recipients=[email],
                subject=_(f"📊 Utility Reading Required: {meter.meter_name}"),
                message=_(
                    "<p>No utility reading has been submitted for meter "
                    "<b>{0}</b> ({1}) at <b>{2}</b> for this month.</p>"
                    "<p>Please submit a reading to keep utility tracking up to date.</p>"
                    "<p><a href='/Form/Utility Consumption/new-utility-consumption-1?"
                    "utility_meter={3}'>Submit Reading →</a></p>"
                ).format(
                    meter.meter_name, meter.meter_type,
                    meter.facility or meter.company, meter.name
                )
            )
    except Exception as e:
        frappe.log_error(f"_alert_missing_utility_readings failed: {e}", "Admin Scheduler")


def _monthly_fleet_summary():
    """
    Send a monthly fleet cost summary to all HR Managers.
    """
    try:
        if not frappe.db.table_exists("tabVehicle Trip Log"):
            return

        from frappe.utils import get_first_day, get_last_day
        month_start = get_first_day(add_days(nowdate(), -1))  # previous month
        month_end   = get_last_day(add_days(nowdate(), -1))

        summary = frappe.db.sql("""
            SELECT
                COUNT(DISTINCT vtl.vehicle) AS vehicles_used,
                COUNT(*) AS total_trips,
                COALESCE(SUM(vtl.distance_km), 0) AS total_km,
                COALESCE(SUM(vtl.fuel_cost), 0) AS total_fuel_cost
            FROM `tabVehicle Trip Log` vtl
            WHERE vtl.docstatus = 1
              AND vtl.trip_date BETWEEN %s AND %s
        """, (month_start, month_end), as_dict=True)

        if not summary or not summary[0].total_trips:
            return

        s = summary[0]

        # Get HR Manager emails
        managers = frappe.db.sql("""
            SELECT DISTINCT u.email
            FROM `tabHas Role` hr
            JOIN `tabUser` u ON u.name = hr.parent
            WHERE hr.role = 'HR Manager'
              AND u.enabled = 1
              AND u.email != 'Administrator'
        """, as_dict=True)

        emails = [m.email for m in managers if m.email]
        if not emails:
            return

        frappe.sendmail(
            recipients=emails,
            subject=_(f"🚗 Monthly Fleet Summary — {month_start.strftime('%B %Y') if hasattr(month_start,'strftime') else month_start}"),
            message=_("""
                <h3>Monthly Fleet Summary</h3>
                <table cellpadding="8" style="border-collapse:collapse;font-size:13px">
                  <tr><td><b>Vehicles Used:</b></td><td>{0}</td></tr>
                  <tr><td><b>Total Trips:</b></td><td>{1}</td></tr>
                  <tr><td><b>Total Distance:</b></td><td>{2:,.1f} km</td></tr>
                  <tr><td><b>Total Fuel Cost:</b></td><td>₦{3:,.0f}</td></tr>
                </table>
                <p><a href='/List/Vehicle Trip Log'>View Trip Logs →</a></p>
            """).format(
                s.vehicles_used, s.total_trips,
                flt(s.total_km), flt(s.total_fuel_cost)
            )
        )
    except Exception as e:
        frappe.log_error(f"_monthly_fleet_summary failed: {e}", "Admin Scheduler")