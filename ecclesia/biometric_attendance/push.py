"""
ADMS Push Receiver — real-time attendance for devices in
sync_mode = "Push (Real-time)".

TAMS Chrome (and any other ZKTeco-firmware device) can be configured under
Comm > Server Settings with a Server IP, Server Port, and an "Enable Proxy
Server" toggle. Pointing the Server IP/Port at this Frappe site's own
address (not TAMS's own cloud) makes the device push punches here directly
— no TAMS API or scheduled pull required, and ERPNext becomes the single
source of truth as intended.

Devices speaking this protocol call two fixed paths, which must be rewritten
at the nginx layer to the whitelisted methods below (device firmware cannot
be told to use /api/method/... directly):

    GET  /iclock/cdata?SN=<serial>&options=all        -> handshake/heartbeat
    POST /iclock/cdata?SN=<serial>&table=ATTLOG        -> attendance push (raw text body)
    GET  /iclock/getrequest?SN=<serial>                -> command poll (we return no-op)

Required nginx addition (in the site's server block, before the main
`location /` block — see deployment note at the bottom of this file):

    location /iclock/ {
        rewrite ^/iclock/cdata(.*)$ /api/method/ecclesia.biometric_attendance.push.cdata$1 last;
        rewrite ^/iclock/getrequest(.*)$ /api/method/ecclesia.biometric_attendance.push.getrequest$1 last;
    }

Trust model: since the device has no login flow, authentication is via
matching the pushed Serial Number (SN) against an enabled Biometric Device
record with that device_serial and sync_mode = "Push (Real-time)". Unknown
serials are rejected with 401 and logged.
"""

import frappe


@frappe.whitelist(allow_guest=True)
def cdata(SN=None, table=None, options=None, **kwargs):
	device = _get_push_device(SN)
	if not device:
		frappe.local.response.http_status_code = 401
		return "Unregistered Device"

	# Any contact at all — handshake or data push — proves the device is
	# alive and reachable right now, regardless of whether there's new
	# attendance data. This is what lets us detect a silently dead device
	# during hours with no punches, which last_sync alone can't do.
	device.db_set("last_heartbeat", frappe.utils.now())
	device.db_set("device_status", "Online")

	request_method = frappe.request.method

	if request_method == "GET":
		if options == "all":
			# Standard ADMS handshake response — tells the device its
			# reporting cadence is accepted; TransFlag/Realtime enable
			# immediate push rather than batching on-device.
			frappe.local.response.mimetype = "text/plain"
			frappe.db.commit()
			return (
				"GET OPTION FROM: SERVER\n"
				"Stamp=9999\n"
				"OpStamp=9999\n"
				"ErrorDelay=30\n"
				"Delay=30\n"
				"TransFlag=1111111111\n"
				"Realtime=1\n"
				"Encrypt=0"
			)
		frappe.db.commit()
		return "OK"

	if request_method == "POST" and table == "ATTLOG":
		body = frappe.request.get_data(as_text=True) or ""
		result = _process_attlog(device, body)
		device.db_set("last_sync", frappe.utils.now())
		frappe.db.commit()
		return f"OK: {result['created']}"

	frappe.db.commit()
	return "OK"


@frappe.whitelist(allow_guest=True)
def getrequest(SN=None, **kwargs):
	"""Devices poll this periodically for pending commands (reboot, user
	sync, etc). We have none queued, so always respond with no-op — but
	this poll is itself a heartbeat, so record it the same way."""
	device = _get_push_device(SN)
	if not device:
		frappe.local.response.http_status_code = 401
		return "Unregistered Device"
	device.db_set("last_heartbeat", frappe.utils.now())
	device.db_set("device_status", "Online")
	frappe.db.commit()
	return "OK"


def _get_push_device(serial):
	if not serial:
		return None
	name = frappe.db.get_value(
		"Biometric Device",
		{
			"device_serial": serial,
			"sync_mode": "Push (Real-time)",
			"enabled": 1,
		},
		"name",
	)
	if not name:
		frappe.log_error(
			f"Push received from unregistered serial: {serial}",
			"Ecclesia ADMS Push Rejected",
		)
		return None
	return frappe.get_doc("Biometric Device", name)


def _process_attlog(device, body):
	"""
	ATTLOG payload: one record per line, tab-separated:
	  PIN\\tTIME\\tSTATUS\\tVERIFY\\t...
	e.g. "12349\\t2026-06-30 08:01:15\\t0\\t1\\t0\\t0\\t0"
	STATUS commonly: 0/4 = Check-In (incl. OT-In), 1/5 = Check-Out (incl.
	OT-Out) — same convention already used by ZKTecoConnector for Pull mode,
	confirm against this specific firmware if attendance looks inverted.
	"""
	from ecclesia.biometric_attendance.sync import record_log

	created = skipped = failed = 0
	errors = []

	for line in body.strip().splitlines():
		parts = line.split("\t")
		if len(parts) < 2:
			continue

		pin, timestamp = parts[0].strip(), parts[1].strip()
		status = parts[2].strip() if len(parts) > 2 else None
		log_type = "IN" if status in ("0", "4") else "OUT" if status in ("1", "5") else "IN"

		status_result, error = record_log(
			device,
			biometric_user_id=pin,
			punch_time=timestamp,
			log_type=log_type,
		)
		if status_result == "created":
			created += 1
		elif status_result == "skipped":
			skipped += 1
		else:
			failed += 1
			if error:
				errors.append(error)

	if errors:
		frappe.log_error(
			"\n".join(errors), f"Ecclesia ADMS Push Errors: {device.name}"
		)

	return {"created": created, "skipped": skipped, "failed": failed}


def flag_offline_push_devices(timeout_minutes=10):
	"""
	Scheduled every 5 minutes (see hooks.py). Push devices are expected to
	heartbeat every ~30 seconds per the Delay=30 handshake response above,
	so any enabled push device with no contact in `timeout_minutes` is very
	likely disconnected, powered off, or repointed away from this server —
	flag it rather than let it silently look 'fine' just because there
	happened to be no punches to report.
	"""
	from frappe.utils import now_datetime, get_datetime

	devices = frappe.get_all(
		"Biometric Device",
		filters={"sync_mode": "Push (Real-time)", "enabled": 1},
		fields=["name", "last_heartbeat", "device_status"],
	)

	for d in devices:
		if d.device_status == "Offline":
			continue  # already flagged, nothing to do

		if not d.last_heartbeat:
			frappe.db.set_value("Biometric Device", d.name, "device_status", "Offline")
			continue

		elapsed_minutes = (
			now_datetime() - get_datetime(d.last_heartbeat)
		).total_seconds() / 60

		if elapsed_minutes > timeout_minutes:
			frappe.db.set_value("Biometric Device", d.name, "device_status", "Offline")

	frappe.db.commit()