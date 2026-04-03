"""
Device Connector Factory
Returns the correct connector class for each brand.

Brand          Protocol          Connector Class
------         --------          ---------------
ZKTeco         SDK / UDP         ZKTecoConnector
eSSL           SDK (ZK-compat)   ZKTecoConnector
Hikvision      ISAPI / REST      HikvisionConnector
Dahua          HTTP API (CGI)    DahuaConnector
Suprema        BioStar2 REST     SupremaConnector
Anviz          CloudClox REST    AnvizConnector
Virdi          REST API          VirdiConnector
Realand        SDK               RealandConnector
Other          HTTP API          GenericHttpConnector
"""
import frappe
from datetime import datetime, timedelta


# ── Factory ───────────────────────────────────────────────────────────────────

def get_connector(device_doc):
    brand = device_doc.device_brand
    CONNECTORS = {
        "ZKTeco":    ZKTecoConnector,
        "eSSL":      ZKTecoConnector,      # eSSL is ZKTeco-protocol compatible
        "Hikvision": HikvisionConnector,
        "Dahua":     DahuaConnector,
        "Suprema":   SupremaConnector,
        "Anviz":     AnvizConnector,
        "Virdi":     VirdiConnector,
        "Realand":   RealandConnector,
        "Other":     GenericHttpConnector,
    }
    cls = CONNECTORS.get(brand)
    if not cls:
        frappe.throw(f"No connector implemented for brand: {brand}")
    return cls(device_doc)


# ── Base ──────────────────────────────────────────────────────────────────────

class BaseConnector:
    """All connectors must implement ping(), get_attendance_logs(), get_users()."""

    def __init__(self, device):
        self.device = device
        self.ip = device.ip_address
        self.port = device.port

    def _scheme(self):
        return "https" if self.device.use_https else "http"

    def _base_url(self):
        return f"{self._scheme()}://{self.ip}:{self.port}"

    def ping(self):
        raise NotImplementedError

    def get_attendance_logs(self, from_date=None):
        raise NotImplementedError

    def get_users(self):
        raise NotImplementedError

    def _default_from(self, from_date=None):
        return from_date or (datetime.now() - timedelta(days=1)).date()


# ── ZKTeco / eSSL  (SDK over UDP/TCP, port 4370) ────────────────────────────

class ZKTecoConnector(BaseConnector):
    """
    Uses pyzk (pip install pyzk).
    Works for ZKTeco and eSSL — both share the same binary SDK protocol.
    """

    def __init__(self, device):
        super().__init__(device)
        self.password = int(device.get_password("communication_key") or 0)

    def _connect(self):
        from zk import ZK
        zk = ZK(self.ip, port=self.port or 4370, timeout=10, password=self.password,
                 force_udp=False, ommit_ping=False)
        return zk.connect()

    def ping(self):
        try:
            conn = self._connect()
            conn.disconnect()
            return True
        except Exception:
            return False

    def get_attendance_logs(self, from_date=None):
        start = self._default_from(from_date)
        conn = self._connect()
        try:
            records = conn.get_attendance()
            logs = []
            for r in records:
                if r.timestamp.date() < start:
                    continue
                logs.append({
                    "biometric_user_id": str(r.user_id),
                    "punch_time": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    # ZKTeco punch codes: 0=Check-In, 1=Check-Out, 4=OT-In, 5=OT-Out
                    "log_type": "IN" if r.punch in (0, 4) else "OUT"
                })
            return logs
        finally:
            conn.disconnect()

    def get_users(self):
        conn = self._connect()
        try:
            return [
                {"uid": str(u.user_id), "name": u.name, "privilege": u.privilege}
                for u in conn.get_users()
            ]
        finally:
            conn.disconnect()


# ── Hikvision  (ISAPI REST, port 80/443) ────────────────────────────────────

class HikvisionConnector(BaseConnector):
    """
    Uses Hikvision ISAPI — HTTP Basic Auth.
    Username = device.username (default: admin)
    Password = device.password
    """

    def __init__(self, device):
        super().__init__(device)
        self.auth = (device.username or "admin", device.get_password("password") or "")

    def _url(self, path):
        return f"{self._base_url()}/ISAPI/{path}"

    def ping(self):
        import requests
        try:
            r = requests.get(self._url("System/status"), auth=self.auth,
                             timeout=5, verify=False)
            return r.status_code == 200
        except Exception:
            return False

    def get_attendance_logs(self, from_date=None):
        import requests
        start = self._default_from(from_date)
        payload = {
            "AcsEventCond": {
                "searchID": "1",
                "searchResultPosition": 0,
                "maxResults": 2000,
                "major": 5,        # 5 = Access Control events
                "startTime": f"{start}T00:00:00+01:00",
                "endTime": f"{datetime.now().date()}T23:59:59+01:00"
            }
        }
        r = requests.post(self._url("ACS/Access/controllerEvent"),
                          json=payload, auth=self.auth, timeout=30, verify=False)
        r.raise_for_status()
        events = r.json().get("AcsEvent", {}).get("InfoList", [])
        logs = []
        for e in events:
            # minor: 75=entry, 76=exit (varies by firmware — adjust as needed)
            log_type = "OUT" if e.get("minor") == 76 else "IN"
            logs.append({
                "biometric_user_id": str(e.get("employeeNoString", "")),
                "punch_time": e.get("time", "").replace("T", " ")[:19],
                "log_type": log_type
            })
        return logs

    def get_users(self):
        import requests
        payload = {"UserInfoSearchCond": {"searchID": "0", "searchResultPosition": 0,
                                           "maxResults": 1000}}
        r = requests.post(self._url("AccessControl/UserInfo/Search"),
                          json=payload, auth=self.auth, timeout=30, verify=False)
        r.raise_for_status()
        users = r.json().get("UserInfoSearch", {}).get("UserInfo", [])
        return [{"uid": u.get("employeeNo"), "name": u.get("name")} for u in users]


# ── Dahua  (HTTP CGI API, port 80/443) ──────────────────────────────────────

class DahuaConnector(BaseConnector):
    """
    Uses Dahua HTTP API (CGI) — HTTP Digest Auth.
    Username = device.username (default: admin)
    Password = device.password
    """

    def __init__(self, device):
        super().__init__(device)
        # Dahua uses HTTP Digest auth
        from requests.auth import HTTPDigestAuth
        self.auth = HTTPDigestAuth(
            device.username or "admin",
            device.get_password("password") or ""
        )

    def _cgi(self, script, **params):
        import requests
        url = f"{self._base_url()}/cgi-bin/{script}.cgi"
        r = requests.get(url, params=params, auth=self.auth, timeout=30, verify=False)
        r.raise_for_status()
        return r.text

    def ping(self):
        try:
            self._cgi("magicBox", action="getSystemInfo")
            return True
        except Exception:
            return False

    def get_attendance_logs(self, from_date=None):
        start = self._default_from(from_date)
        raw = self._cgi(
            "attendanceRecord",
            action="find",
            object="AttendanceRecord",
            StartTime=f"{start} 00:00:00",
            EndTime=f"{datetime.now().date()} 23:59:59"
        )
        logs = []
        # Dahua returns key=value pairs, one record per line
        record = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                if record:
                    logs.append({
                        "biometric_user_id": record.get("UserID", ""),
                        "punch_time": record.get("Time", ""),
                        # Dahua Type: 0=Check-In, 1=Check-Out, 2=OT-In, 3=OT-Out
                        "log_type": "OUT" if record.get("Type") in ("1", "3") else "IN"
                    })
                    record = {}
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                record[k.split(".")[-1]] = v.strip()
        return logs

    def get_users(self):
        raw = self._cgi("userManager", action="getUserInfoAll")
        users = []
        uid, name = None, None
        for line in raw.splitlines():
            if "UserID" in line:
                uid = line.split("=")[-1].strip()
            if "UserName" in line:
                name = line.split("=")[-1].strip()
            if uid and name:
                users.append({"uid": uid, "name": name})
                uid, name = None, None
        return users


# ── Suprema  (BioStar2 REST API, port 443) ───────────────────────────────────

class SupremaConnector(BaseConnector):
    """
    Uses Suprema BioStar2 REST API.
    Requires BioStar2 server URL + API credentials.
    device.biostar_server_url e.g. https://biostar2.yourcompany.com
    device.username + device.password — BioStar2 login
    Logs in once to get session cookie / Bearer token.
    """

    def __init__(self, device):
        super().__init__(device)
        self._server = (device.biostar_server_url or "").rstrip("/")
        self._username = device.username or ""
        self._secret = device.get_password("password") or ""
        self._token = None

    def _login(self):
        import requests
        r = requests.post(
            f"{self._server}/api/login",
            json={"User": {"login_id": self._username, "password": self._secret}},
            verify=False, timeout=15
        )
        r.raise_for_status()
        data = r.json()
        self._token = data.get("Response", {}).get("session")
        if not self._token:
            frappe.throw("BioStar2 login failed — check credentials.")

    def _headers(self):
        if not self._token:
            self._login()
        return {"bs-session-id": self._token, "Content-Type": "application/json"}

    def ping(self):
        import requests
        try:
            self._login()
            return bool(self._token)
        except Exception:
            return False

    def get_attendance_logs(self, from_date=None):
        import requests
        start = self._default_from(from_date)
        payload = {
            "EventLogSearch": {
                "start_datetime": f"{start}T00:00:00.000Z",
                "end_datetime": f"{datetime.now().date()}T23:59:59.000Z",
                "event_type_list": [{"code": "0x1000"}],  # Entry events
                "max_count": 5000
            }
        }
        r = requests.post(f"{self._server}/api/events/search",
                          json=payload, headers=self._headers(),
                          verify=False, timeout=30)
        r.raise_for_status()
        rows = r.json().get("EventLogSearch", {}).get("rows", [])
        logs = []
        for row in rows:
            event_type = row.get("event_type", {}).get("code", "")
            # BioStar2: 0x1000=Entry, 0x2000=Exit
            log_type = "OUT" if event_type == "0x2000" else "IN"
            logs.append({
                "biometric_user_id": str(row.get("user_id", {}).get("user_id", "")),
                "punch_time": row.get("datetime", "").replace("T", " ")[:19],
                "log_type": log_type
            })
        return logs

    def get_users(self):
        import requests
        r = requests.get(f"{self._server}/api/users",
                         headers=self._headers(), verify=False, timeout=30)
        r.raise_for_status()
        rows = r.json().get("UserCollection", {}).get("rows", [])
        return [{"uid": u.get("user_id"), "name": u.get("name")} for u in rows]


# ── Anviz  (CloudClox REST API) ───────────────────────────────────────────────

class AnvizConnector(BaseConnector):
    """
    Uses Anviz CloudClox cloud API.
    device.cloudclox_api_url  — API base (default: https://api.cloudclox.com)
    device.cloudclox_device_id — Device ID from CloudClox portal
    device.api_key — CloudClox API key
    No direct IP connection — everything goes via cloud.
    """

    def __init__(self, device):
        super().__init__(device)
        self._api_url = (device.cloudclox_api_url or "https://api.cloudclox.com").rstrip("/")
        self._device_id = device.cloudclox_device_id or ""
        self._api_key = device.get_password("api_key") or ""

    def _headers(self):
        return {"Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"}

    def ping(self):
        import requests
        try:
            r = requests.get(
                f"{self._api_url}/v2/device/{self._device_id}/status",
                headers=self._headers(), timeout=10
            )
            data = r.json()
            return data.get("data", {}).get("online", False)
        except Exception:
            return False

    def get_attendance_logs(self, from_date=None):
        import requests
        start = self._default_from(from_date)
        params = {
            "device_id": self._device_id,
            "start_time": f"{start} 00:00:00",
            "end_time": f"{datetime.now().date()} 23:59:59",
            "page": 1,
            "page_size": 1000
        }
        r = requests.get(f"{self._api_url}/v2/attendance/records",
                         params=params, headers=self._headers(), timeout=30)
        r.raise_for_status()
        records = r.json().get("data", {}).get("list", [])
        logs = []
        for rec in records:
            # Anviz check_type: 0=Check-In, 1=Check-Out
            log_type = "OUT" if rec.get("check_type") == 1 else "IN"
            logs.append({
                "biometric_user_id": str(rec.get("employee_id", "")),
                "punch_time": rec.get("check_time", ""),
                "log_type": log_type
            })
        return logs

    def get_users(self):
        import requests
        r = requests.get(
            f"{self._api_url}/v2/employees",
            params={"device_id": self._device_id, "page_size": 1000},
            headers=self._headers(), timeout=30
        )
        r.raise_for_status()
        rows = r.json().get("data", {}).get("list", [])
        return [{"uid": str(u.get("employee_id")), "name": u.get("name")} for u in rows]


# ── Virdi  (REST API, port 80/443) ────────────────────────────────────────────

class VirdiConnector(BaseConnector):
    """
    Uses Virdi UBio-X / AC Series REST API.
    device.username + device.api_key (Bearer token from Virdi server login)
    """

    def __init__(self, device):
        super().__init__(device)
        self._token = device.get_password("api_key") or ""
        self._username = device.username or "admin"
        self._password = device.get_password("password") or ""

    def _headers(self):
        if not self._token:
            self._do_login()
        return {"Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json"}

    def _do_login(self):
        import requests
        r = requests.post(
            f"{self._base_url()}/api/login",
            json={"username": self._username, "password": self._password},
            verify=False, timeout=15
        )
        r.raise_for_status()
        self._token = r.json().get("token", "")

    def ping(self):
        import requests
        try:
            r = requests.get(f"{self._base_url()}/api/system/info",
                             headers=self._headers(), verify=False, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def get_attendance_logs(self, from_date=None):
        import requests
        start = self._default_from(from_date)
        params = {
            "startDate": str(start),
            "endDate": str(datetime.now().date())
        }
        r = requests.get(f"{self._base_url()}/api/attendance/log",
                         params=params, headers=self._headers(),
                         verify=False, timeout=30)
        r.raise_for_status()
        records = r.json().get("data", [])
        logs = []
        for rec in records:
            # Virdi eventType: 0=Entry, 1=Exit (confirm per firmware docs)
            log_type = "OUT" if rec.get("eventType") == 1 else "IN"
            logs.append({
                "biometric_user_id": str(rec.get("userId", "")),
                "punch_time": rec.get("eventTime", ""),
                "log_type": log_type
            })
        return logs

    def get_users(self):
        import requests
        r = requests.get(f"{self._base_url()}/api/users",
                         headers=self._headers(), verify=False, timeout=30)
        r.raise_for_status()
        return [{"uid": str(u.get("userId")), "name": u.get("name")}
                for u in r.json().get("data", [])]


# ── Realand  (SDK — similar binary protocol to ZKTeco) ───────────────────────

class RealandConnector(BaseConnector):
    """
    Realand devices use a binary SDK protocol similar to ZKTeco.
    pyzk works for most Realand models (tested on A-C series).
    Falls back gracefully if model is incompatible.
    """

    def __init__(self, device):
        super().__init__(device)
        self.password = int(device.get_password("communication_key") or 0)

    def _connect(self):
        from zk import ZK
        zk = ZK(self.ip, port=self.port or 4370, timeout=10,
                 password=self.password, force_udp=True)
        return zk.connect()

    def ping(self):
        try:
            conn = self._connect()
            conn.disconnect()
            return True
        except Exception:
            return False

    def get_attendance_logs(self, from_date=None):
        start = self._default_from(from_date)
        conn = self._connect()
        try:
            records = conn.get_attendance()
            logs = []
            for r in records:
                if r.timestamp.date() < start:
                    continue
                logs.append({
                    "biometric_user_id": str(r.user_id),
                    "punch_time": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "log_type": "IN" if r.punch in (0, 4) else "OUT"
                })
            return logs
        finally:
            conn.disconnect()

    def get_users(self):
        conn = self._connect()
        try:
            return [{"uid": str(u.user_id), "name": u.name} for u in conn.get_users()]
        finally:
            conn.disconnect()


# ── Generic HTTP  (for "Other" brand devices) ────────────────────────────────

class GenericHttpConnector(BaseConnector):
    """
    Fallback connector for unlisted brands with a REST-ish HTTP API.
    Override get_attendance_logs() and get_users() in a subclass
    or configure via device notes field.
    """

    def __init__(self, device):
        super().__init__(device)
        self._token = device.get_password("api_key") or ""
        self.auth = (device.username or "", device.get_password("password") or "")

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def ping(self):
        import requests
        try:
            r = requests.get(self._base_url(), auth=self.auth or None,
                             headers=self._headers(), timeout=5, verify=False)
            return r.status_code < 500
        except Exception:
            return False

    def get_attendance_logs(self, from_date=None):
        frappe.throw(
            f"GenericHttpConnector: implement get_attendance_logs() for your device brand."
        )

    def get_users(self):
        frappe.throw(
            f"GenericHttpConnector: implement get_users() for your device brand."
        )