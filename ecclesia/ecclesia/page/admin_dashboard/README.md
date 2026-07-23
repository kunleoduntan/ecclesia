# Admin 360° Power Dashboard — Installation Guide

## Files
| File | Purpose |
|------|---------|
| `admin_dashboard.js` | Full 2,233-line client-side dashboard (10 tabs, 9 themes, Chart.js) |
| `admin_dashboard.py` | Frappe page controller (minimal — all logic is client-side) |
| `admin_dashboard.json` | Page definition for Frappe desk |

## Installation

### 1. Copy to app
```bash
mkdir -p /apps/ecclesia/ecclesia/ecclesia/page/admin_dashboard/
cp admin_dashboard.js  /apps/ecclesia/ecclesia/ecclesia/page/admin_dashboard/
cp admin_dashboard.py  /apps/ecclesia/ecclesia/ecclesia/page/admin_dashboard/
cp admin_dashboard.json /apps/ecclesia/ecclesia/ecclesia/page/admin_dashboard/
```

### 2. Register in hooks.py
```python
# ecclesia/hooks.py
page_js = {
    "admin-dashboard": "public/js/admin_dashboard.js"
}
```
Or simply ensure the page folder is in the app — Frappe auto-discovers page JS files.

### 3. Migrate
```bash
bench --site yoursite.com migrate
bench --site yoursite.com clear-cache
```

### 4. Access
Navigate to: `yoursite.com/admin-dashboard`
Or: Desk → Search → "Admin 360° Dashboard"

---

## 10 Dashboard Tabs

| Tab | DocTypes Queried | Key Features |
|-----|-----------------|--------------|
| 🏠 Overview | All 18 DocTypes | 8 KPIs, spend donut, activity chart, compliance radar |
| 📋 Requests | Administrative Request | Full CRUD table, SLA tracker, pipeline funnel, type bar chart |
| 🚗 Fleet | Company Vehicle, Vehicle Trip Log, Fuel Issue | Fleet status grid, expiry alerts, fuel cost bar chart |
| 🏗 Facilities | Facility, Facility Maintenance Request, Maintenance Work Order, Meeting Room Booking | Facility table, maintenance by category donut, work orders |
| ⚡ Utilities | Utility Consumption, Utility Meter, Generator Log | 6-month trend line, MTD breakdown, generator analysis, diesel cost |
| 🛡 Security | Security Incident, Visitor Register | Incident table, severity pie, visitor trend bar chart |
| 📑 Contracts | Service Contract, Service Provider | Contract expiry table, spend by type bars, vendor list |
| 🎖 Compliance | Compliance Register | Sortable register, items by type donut, action-required alerts |
| ⚠️ HSE | HSE Inspection, Asset Inspection | Inspection table with score bars, facility HSE scores, asset conditions |
| 🤖 AI Intelligence | All 18 (aggregated) | Health score, SLA risk, utility anomalies, predictive maintenance, Anthropic AI deep analysis |

---

## 9 Themes (localStorage only)
`steel` · `midnight` · `verdant` · `ember` · `nova` · `arctic` · `forest` · `sunset` · `candy`

Theme is stored in `localStorage` key `admin-dash-theme`. No database writes.

---

## AI Intelligence Tab
The "✨ Deep Analysis" button calls:
```
POST /api/method/ecclesia.api.ai_diagnosis.get_ai_insight
```
This is the same whitelisted Anthropic API endpoint used in your PROD intelligence and church CRM pages.

Falls back gracefully to client-side pattern-matching insights if the API call fails.

---

## Auto-Refresh
Data refreshes every 30 seconds silently in the background.
The banner shows "Updated HH:MM:SS" on each refresh.

---

## DocTypes Required (all from ecclesia_admin_doctypes.zip)
Administrative Request · Company Vehicle · Vehicle Trip Log · Fuel Issue ·
Facility · Facility Maintenance Request · Maintenance Work Order · Utility Meter ·
Utility Consumption · Generator Log · Visitor Register · Security Incident ·
Service Contract · Service Provider · Compliance Register · Asset Inspection ·
HSE Inspection · Meeting Room Booking
