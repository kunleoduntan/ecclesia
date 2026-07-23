# Ecclesia WFH Module — User Manual
**Version 1.0 | ERPNext 14/15**

---

## Table of Contents

1. [Overview](#1-overview)
2. [Roles & Permissions](#2-roles--permissions)
3. [Getting Started — First-Time Setup](#3-getting-started--first-time-setup)
4. [Daily Employee Workflow](#4-daily-employee-workflow)
5. [Manager Workflow](#5-manager-workflow)
6. [HR Manager Workflow](#6-hr-manager-workflow)
7. [WFH Activity Mapping (Admin)](#7-wfh-activity-mapping-admin)
8. [Activity Configuration (Scoring)](#8-activity-configuration-scoring)
9. [Reports](#9-reports)
10. [WFH Dashboard](#10-wfh-dashboard)
11. [GPS Location (Optional)](#11-gps-location-optional)
12. [Notifications & Reminders](#12-notifications--reminders)
13. [Compliance & Flags](#13-compliance--flags)
14. [Troubleshooting](#14-troubleshooting)
15. [Module File Reference](#15-module-file-reference)

---

## 1. Overview

The Ecclesia WFH Module provides end-to-end remote work tracking inside ERPNext. It combines:

- **Authorisation** — WFH Requests approved by HR or Line Managers
- **Presence** — Daily check-in and check-out via WFH Sessions
- **Passive activity capture** — Work Activity Logs auto-generated whenever employees submit, update or create configured ERPNext documents
- **Light daily declaration** — WFH Daily Summary (30–60 seconds per day)
- **Intelligence** — Scoring, composite scores, compliance tracking, flags

Everything works without GPS. Location capture is a supplementary feature that employees can optionally grant.

---

## 2. Roles & Permissions

| Role | Create | Own records | Team records | Approve | Full access |
|---|---|---|---|---|---|
| Employee | ✓ | ✓ | — | — | — |
| Line Manager | ✓ | ✓ | ✓ | ✓ | — |
| HR Manager | ✓ | ✓ | ✓ | ✓ | — |
| System Manager | ✓ | ✓ | ✓ | ✓ | ✓ |

**Assign roles in:** ERPNext → Settings → User → Roles

**Row-level security:** Employees automatically see only their own records. Line Managers see their direct reportees (based on the `reports_to` field on the Employee DocType).

---

## 3. Getting Started — First-Time Setup

Complete these steps once after installing the module.

### Step 1 — Run migrations
```bash
bench --site your-site.local migrate
```
This creates all DocTypes and injects the `wfh_request` custom field into Attendance.

### Step 2 — Seed Activity Mappings
Navigate to: **Ecclesia → WFH Management → WFH Activity Mapping**

Click **Tools → Seed Default Mappings**. This adds 14 standard ERPNext DocTypes (Sales Invoice, Lead, Payment Entry, etc.) to the tracking table. You can add or remove DocTypes at any time — changes take effect within 5 minutes with no restart needed.

### Step 3 — Seed Scoring Configurations
From the Activity Engine, run once via bench console:
```python
frappe.call("ecclesia.api.engine.seed_default_configurations")
```
Or navigate to **Activity Configuration** and create records manually.

### Step 4 — Add the Attendance status option
In ERPNext Property Setter, add `Work From Home` to the Attendance Status select field options. Alternatively, the module's fixture export handles this automatically.

### Step 5 — Set up notifications (optional)
Navigate to **Setup → Notification** and create notifications using the WFH Request and WFH Daily Summary DocTypes as triggers. See Section 12 for templates.

### Step 6 — Configure inactivity threshold
In **WFH Activity Mapping**, set **Inactivity Flag Threshold (hours)**. Default is 3. Sessions idle beyond this threshold are automatically flagged by the hourly scheduler.

---

## 4. Daily Employee Workflow

This is the standard day for an employee working from home.

### 4.1 Submit a WFH Request (first time or new period)

1. Go to **Ecclesia → WFH Management → New WFH Request**
2. Fill in: From Date, To Date, Work Mode (Fully Remote / Hybrid), Reason
3. Optionally add Expected Deliverables
4. Click **Submit for Approval** (Actions menu)
5. Your approver is auto-detected from your `reports_to` field. You will receive an email when approved or rejected.

> You only need a new WFH Request when starting a new approved period. You do not need one every day.

### 4.2 Check in — start your WFH Session

**From the form:**
1. Go to **WFH Session → New**
2. Your employee name and today's date are pre-filled
3. Your approved WFH Request is auto-linked
4. Click **Save** — check-in time is recorded automatically

**From the dashboard:**
1. Go to **WFH Dashboard**
2. Click **Check in with GPS** — if you grant location permission, coordinates are saved. If you deny or skip, check-in proceeds normally

> A session without GPS is fully valid. The GPS pin is informational only.

### 4.3 Work normally

The system silently logs your ERPNext activity in the background. Every time you submit a Sales Invoice, update an Opportunity, post a Payment Entry, etc., a Work Activity Log entry is created and points are awarded — no action needed from you.

### 4.4 Submit your Daily Summary (before 5 PM)

1. Go to **WFH Daily Summary → New**
2. Your session is auto-linked if you checked in today
3. Fill in **Key Achievements Today** (2–3 sentences)
4. Optionally add Challenges and Tomorrow Plan
5. Give yourself a **Self Rating** (1–5 stars)
6. Click **Save**, then **Submit**

This takes 30–60 seconds. A reminder email is sent at ~5 PM if you haven't submitted.

### 4.5 Check out

**From the WFH Session form:** Click **Check Out Now**

**From the dashboard:** Click your active session chip, then Check Out

Total hours are calculated automatically.

---

## 5. Manager Workflow

### 5.1 Approve WFH Requests

1. Go to **Ecclesia → WFH Management → Pending Approvals** shortcut, or open **WFH Request** list filtered by Status = Pending Approval
2. Open the request
3. Click **Actions → Approve** or **Actions → Reject** (with reason)
4. An email notification is sent to the employee automatically

### 5.2 Review team activity

**WFH Dashboard** → filter by your department to see:
- Who is checked in today
- Each employee's points and hours
- Flagged sessions and missing summaries

**Productivity Report** → detailed per-day, per-employee breakdown with hours, points, business value, and composite score.

### 5.3 Review Daily Summaries

1. Open **WFH Daily Summary** list
2. Filter by your department and date range
3. Open a submitted summary
4. Click **Mark as Reviewed** to confirm you have read it

### 5.4 Handle flags

Employees are flagged when:
- Their session has been idle (no activity) for longer than the inactivity threshold
- Their summary has anomalies (high hours, zero points, etc.)

Open the flagged session or summary, review, and either clear the flag manually or send feedback to the employee.

---

## 6. HR Manager Workflow

### 6.1 Full visibility

HR Managers see all employees across all departments in every list and report. No User Permission filters are applied.

### 6.2 Monthly compliance review

Run **Compliance Report** with the current month's date range. The report shows for every WFH attendance day:
- Whether an approved request exists
- Whether a session was logged
- Whether a summary was submitted and reviewed
- A compliance score (0–100) per day
- A summary of all issues

Export failed rows to CSV using the **Export Failed Only** button for HR action.

### 6.3 Payroll integration

When a WFH Request is approved, Attendance records with status `Work From Home` are created automatically for each day in the approved range. These integrate with ERPNext's standard payroll processing. No manual Attendance entry is needed.

### 6.4 WFH Activity Mapping management

See Section 7.

---

## 7. WFH Activity Mapping (Admin)

Navigate to: **Ecclesia → WFH Management → WFH Activity Mapping**

This is a single settings page that controls the entire passive tracking engine.

### Global settings

| Setting | Default | Description |
|---|---|---|
| Enable Activity Tracking | On | Master switch — turn off to pause all logging |
| Track Only During WFH Sessions | On | When on, only logs activity if employee has an open session today |
| Default Daily Points Cap | 200 | Max points per employee per day (fallback if no Activity Configuration) |
| Inactivity Flag Threshold | 3 hours | Sessions idle longer than this are auto-flagged |

### Adding a DocType to track

1. Click **Add Row** in the Mappings table
2. Type the DocType name (e.g. `Sales Invoice`) — the module is auto-detected
3. Tick the events you want to capture:
   - **On Submit** — when a document is submitted (recommended for transactional DocTypes)
   - **On Cancel** — when a document is cancelled
   - **On Update/Save** — when a document is saved (recommended for CRM DocTypes like Lead)
   - **On Create** — when a new document is first inserted
4. Click **Save** — changes are live within 5 minutes (no restart)

The `Has Activity Config` column shows automatically whether a scoring configuration exists for each DocType. If missing, a direct link to create one appears.

### Removing a DocType

Either untick **Active** on the row (keeps it for future re-activation) or delete the row entirely. Changes take effect within 5 minutes.

### Flushing the cache manually

**Tools → Flush Runtime Cache** forces the engine to reload immediately (bypasses the 5-minute TTL).

---

## 8. Activity Configuration (Scoring)

Navigate to: **Ecclesia → Activity Configuration**

One record per tracked DocType. Controls how many points are awarded.

### Points Rule options

| Rule | How it works | Use when |
|---|---|---|
| Fixed | Base Points awarded per action | Simple, consistent actions (Payment Entry, Stock Entry) |
| Formula | Base Points + value-based bonus | High-value transactions (Sales Invoice, Sales Order) |
| Percentage of Value | % of the document's monetary value | When you want points proportional to deal size |

### Formula mode (recommended for sales)

- **Base Points** — floor award per action (e.g. 10)
- **Value Field** — the monetary field on the DocType (e.g. `grand_total`)
- **Value Divisor** — bonus = value ÷ divisor (e.g. divisor 100,000 = 1 point per ₦100k)
- **Max Value Bonus** — cap the bonus (prevents gaming with a single huge invoice)

### Frequency dampening

Prevents gamification by repeated low-effort actions.

- **Dampening Window** — look-back period in minutes (e.g. 30)
- **Dampening Multiplier** — applied after 3+ identical actions in the window (e.g. 0.5 = half points)
- **Daily Cap** — absolute ceiling on points from this DocType per employee per day

### Role weights

Override points per role. Example: give Sales staff 1.2× weight on Sales Invoice points, while giving Finance staff 0.8× to reflect different workload expectations.

### Test Scorer

Use **Tools → Test Scorer** to preview exactly how many points a specific employee would earn for a specific transaction value before going live.

---

## 9. Reports

All reports are under **Ecclesia → WFH Management** workspace.

### WFH Summary Report

**Purpose:** Period overview per employee.

**Key columns:** Employee, Department, WFH Days, Total Hours, Avg Hours/Day, Activity Points, Business Value, Summaries Submitted, Compliance %, Avg Composite Score, Days Flagged

**Filters:** Date range, Department, Employee

**Use for:** Monthly HR review, payroll validation, performance conversations

### Productivity Report

**Purpose:** Daily per-employee activity detail.

**Key columns:** Date, Employee, Department, Hours, Check-in, Check-out, Activity Count, Points, Business Value, Top Module, Summary Status, Self Rating, Composite Score

**Filters:** Date range, Employee, Department, Module

**Use for:** Manager daily review, identifying low-output days, checking session quality

**Quick filters:** Today / This Week buttons in the toolbar

### Compliance Report

**Purpose:** Audit trail — did each employee follow the complete WFH process?

**Key columns:** Date, Employee, WFH Approved (✓/✗), Session Exists (✓/✗), Hours, Summary Submitted (✓/✗), Activity Points, Flagged, Compliance Score (0–100), Issues

**Filters:** Date range, Employee, Department, Compliance Level band

**Use for:** Monthly HR compliance audit, identifying process gaps

**Export Failed Only button:** Downloads a CSV of rows with compliance score < 50.

### WFH Command Center

**Purpose:** Real-time management dashboard report.

**Shows:** Today's top performers, active session count, total hours, total points, business value, flagged employees, pending summaries, department breakdown.

**Refreshes:** Automatically every 60 seconds.

---

## 10. WFH Dashboard

Navigate to: **Ecclesia → WFH Dashboard** (or `/app/wfh-dashboard`)

### KPI Cards (top row)

| Card | What it shows |
|---|---|
| Total WFH Days | Distinct employee-day combinations in the selected period |
| Total Hours Logged | Sum of session hours across all employees |
| Activity Points | Total points earned from all tracked ERPNext actions |
| Business Value | Total monetary value of tracked transactions |
| Avg Composite Score | Average of all employees' daily composite scores |
| Compliance Rate | % of WFH days with a submitted/reviewed summary |

### Charts

- **Activity Trend** — daily points and hours over the last 30 days. Toggle between line and bar view.
- **Points by Module** — doughnut showing which ERPNext module generated the most points (Sales, Accounts, CRM, etc.)

### Panels

- **Top Performers** — ranked by total points, with score bar and composite score
- **Flags & Alerts** — inactivity flags and summary anomalies
- **Live Activity Feed** — last 15 Work Activity Log entries in real time
- **Department Breakdown** — bar chart of points by department
- **Compliance Summary** — sessions, summaries, requests at a glance
- **Active Sessions Today** — grid of all employees currently checked in

### Filters

Use the date range, department, and employee filters to drill down. Quick buttons: **Today**, **This Week**, **This Month**.

### AI Insights

Click **Menu → AI Insights** for a generated analysis of the current data including compliance warnings, top performer highlights, department leaders, and actionable recommendations.

### Export / Print

- **Menu → Export CSV** — downloads a summary CSV of all KPIs and top performers
- **Menu → Print Report** — opens a print-formatted version of the dashboard data

---

## 11. GPS Location (Optional)

GPS capture is a supplementary feature. The entire module works fully without it.

### What GPS does

When an employee grants browser location permission during check-in, their coordinates (latitude, longitude, accuracy) are stored on the WFH Session. A GPS pin icon appears next to their name in the dashboard's Today panel.

### What GPS does NOT do

- It does not block check-in if permission is denied
- It does not create a flag or warning for sessions without GPS
- It is not used in compliance scoring
- It is not required for any report, summary, or payroll integration

### How to enable GPS on check-in

**From the WFH Dashboard:**
1. Click **Check in with GPS**
2. Browser prompts for location permission — click Allow
3. Coordinates are saved to the session and the map dot is updated

**From the WFH Session form:**
1. Check in normally (save the form)
2. If session is still Open and GPS was not captured, an **Add GPS location** button appears
3. Click it — browser prompts for permission
4. If allowed, coordinates are saved silently

### When GPS fails or is denied

A grey informational message appears: *"Location permission denied — session continues normally."*

No error is raised. No flag is set. The session proceeds as normal.

### Privacy note

Coordinates are stored only on the WFH Session record in your ERPNext database. They are visible to HR Managers and System Managers. Employees can see their own coordinates.

---

## 12. Notifications & Reminders

### Automatic email notifications

| Trigger | Recipient | Content |
|---|---|---|
| WFH Request submitted | Approver | Request details + approve/reject link |
| WFH Request approved | Employee | Approval confirmation + dates |
| WFH Request rejected | Employee | Rejection reason |
| Missing Daily Summary (5 PM) | Employee | Reminder to submit before end of day |

### Configuring notifications

Navigate to **Setup → Notification** and create Notification records for the WFH Request and WFH Daily Summary DocTypes.

### Scheduler reference

| Schedule | Function | Purpose |
|---|---|---|
| Hourly | `flag_inactive_sessions` | Flags sessions idle > threshold |
| Daily (long) | `send_summary_reminders` | 5 PM reminder emails |
| Weekly | `recompute_weekly_consistency` | Refreshes consistency scores |

---

## 13. Compliance & Flags

### Compliance score (per day, per employee)

Each WFH attendance day receives a score calculated in the Compliance Report:

| Check | Points deducted if missing |
|---|---|
| Approved WFH Request linked | −25 |
| Session (check-in) exists | −30 |
| Daily Summary submitted | −30 |
| No flags on session or summary | −15 |

**100 = fully compliant. Anything below 50 is highlighted as failed.**

### Flag types

| Flag | Raised by | Reason |
|---|---|---|
| Inactivity | Hourly scheduler | Session open with no Work Activity Log for > threshold hours |
| Summary Flagged | Daily Summary controller | High hours + zero activity, or inactivity flag on session |
| High hrs / low output | Summary controller | ≥ 6 hours logged but < 5 activity points |

### GPS and flags

GPS absence is **never** a flag reason. `gps_verified = 0` is normal. Only inactivity and summary anomalies trigger flags.

---

## 14. Troubleshooting

### "Failed to get method" error

**Cause:** Module path is doubled (e.g. `ecclesia.ecclesia.doctype...`).

**Fix:** In all `frappe.call` method strings, use the path starting after the app root:
```
# Correct
ecclesia.doctype.wfh_activity_mapping.wfh_activity_mapping.get_mapping_status

# Wrong (ERPNext doubles the app name automatically)
ecclesia.ecclesia.doctype.wfh_activity_mapping...
```

### Activity logs not being created

Check in order:
1. **WFH Activity Mapping** — is the master switch on? Is the DocType in the table with the correct event ticked?
2. **Activity Configuration** — does a record exist for that DocType with `is_active = 1`?
3. **WFH Session** — does the employee have an open session today? (Only required if "Track Only During WFH Sessions" is on)
4. **Employee link** — does the user performing the action have an Employee record with their user ID linked?
5. **Cache** — click **Tools → Flush Runtime Cache** in WFH Activity Mapping and try again

### Attendance not created after approval

The WFH Request controller auto-creates Attendance on approval. If it fails:
- Check that the employee exists and is active
- Check that no duplicate Attendance record exists for those dates
- Review the Error Log: **Setup → Error Log**

### Session opened but no WFH Request linked

This is normal if "Strict Mode" is off (default). The session is valid.
If you want to enforce requests, enable `wfh_strict_mode` in HR Settings.

### Daily Summary shows 0 activity points

The summary pulls activity score from Work Activity Logs on save. If logs were created after the summary was saved, re-save the summary to refresh the scores.

### GPS check-in not working

GPS requires HTTPS. On a local development server (HTTP), `navigator.geolocation` is blocked by the browser. Either:
- Use HTTPS locally (e.g. `bench setup-https`)
- Or skip GPS and check in normally — the session is fully valid without it

---

## 15. Module File Reference

```
ecclesia/
├── hooks.py                              ← Central wiring (wildcard events)
├── permissions.py                        ← Row-level security helpers
│
├── api/
│   ├── __init__.py
│   ├── engine.py                         ← Passive activity tracking engine
│   └── analytics.py                      ← Aggregation & dashboard queries
│
├── doctype/
│   ├── wfh_request/
│   │   ├── wfh_request.json              ← DocType definition
│   │   ├── wfh_request.py                ← Controller (approval, attendance)
│   │   └── wfh_request.js                ← Client script
│   │
│   ├── wfh_session/
│   │   ├── wfh_session.json              ← DocType definition (GPS fields optional)
│   │   ├── wfh_session.py                ← Controller + check_in/check_out API
│   │   └── wfh_session.js                ← Client script (GPS-optional flow)
│   │
│   ├── work_activity_log/
│   │   ├── work_activity_log.json        ← Read-only auto-generated logs
│   │   ├── work_activity_log.py          ← (minimal controller)
│   │   └── work_activity_log.js          ← Score breakdown display
│   │
│   ├── wfh_daily_summary/
│   │   ├── wfh_daily_summary.json
│   │   ├── wfh_daily_summary.py          ← Composite score, flags, reminders
│   │   └── wfh_daily_summary.js          ← Session auto-link, score preview
│   │
│   ├── activity_configuration/
│   │   ├── activity_configuration.json   ← Scoring rules per DocType
│   │   ├── activity_configuration.py     ← Validation + preview_score API
│   │   └── activity_configuration.js     ← Dynamic fields, test scorer
│   │
│   ├── wfh_activity_mapping/
│   │   ├── wfh_activity_mapping.json     ← Single DocType (settings page)
│   │   ├── wfh_activity_mapping.py       ← Runtime cache, seed, flush API
│   │   └── wfh_activity_mapping.js       ← Status panel, grid auto-detection
│   │
│   └── wfh_doctype_event_map/
│       └── wfh_doctype_event_map.json    ← Child table for mappings
│
├── report/
│   ├── wfh_summary_report/
│   │   ├── wfh_summary_report.json
│   │   ├── wfh_summary_report.py
│   │   └── wfh_summary_report.js
│   ├── productivity_report/
│   │   ├── productivity_report.json
│   │   ├── productivity_report.py
│   │   └── productivity_report.js
│   ├── compliance_report/
│   │   ├── compliance_report.json
│   │   ├── compliance_report.py
│   │   └── compliance_report.js
│   └── wfh_command_center/
│       ├── wfh_command_center.json
│       ├── wfh_command_center.py
│       └── wfh_command_center.js
│
├── page/
│   └── wfh_dashboard/
│       ├── wfh_dashboard.json
│       ├── wfh_dashboard.py
│       └── wfh_dashboard.js
│
└── workspace/
    └── wfh_management.json
```

---

*Ecclesia WFH Module — built for ERPNext 14/15*
*GPS is optional. All features work without location permission.*
