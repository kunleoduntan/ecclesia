# ecclesia/ecclesia/doctype/bank_statement_upload/parser.py
"""
Bank statement parser — ML-enhanced, multi-format, zero-config.

Features:
  - Magic-byte file type detection (handles misnamed files)
  - Multi-engine Excel reading: openpyxl → xlrd → pandas waterfall
  - ML fuzzy column header matching (no manual mapping needed)
  - European vs US number format auto-detection
  - 18 date formats + Excel serial number support
  - 14 currency patterns
  - Parenthesised negative amounts  e.g. (500.00)
  - MT940, OFX, CSV, XLSX, XLS support
  - Inline bank account fuzzy matching

Returned row keys (consumed by ai_coder.analyse_rows):
  transaction_date, raw_narration, debit_amount, credit_amount,
  bank_account_raw, reference_no, running_balance,
  payment_currency, fx_hint
"""

import frappe
import re
import os
import hashlib
from frappe.utils import flt
from datetime import datetime
from difflib import SequenceMatcher


# ================================================================== #
#  SEMANTIC COLUMN VOCABULARIES                                        #
# ================================================================== #

_COL_VOCAB = {
    "date": [
        "date","trans date","transaction date","value date","posting date",
        "book date","trn date","txn date","tran date","entry date",
        "trade date","settlement date","effective date","process date",
        "processed date","booking date","val date","trandate","valuedate",
    ],
    "narration": [
        "description","narration","details","remarks","particulars",
        "transaction description","transaction details","memo","narrative",
        "payment details","beneficiary","purpose","note","notes","info",
        "information","trans desc","trn desc","txn desc","payee","payer",
        "beneficiary name","transaction narration","remark",
    ],
    "debit": [
        "debit","debit amount","withdrawal","withdrawals","dr","dr amount",
        "amount dr","payment out","paid out","debit (ngn)","dr (ngn)",
        "charge","outflow","amount debited","money out","deductions",
        "debit side","dr side","out","outgoing",
    ],
    "credit": [
        "credit","credit amount","deposit","deposits","cr","cr amount",
        "amount cr","payment in","paid in","credit (ngn)","cr (ngn)",
        "inflow","amount credited","money in","receipts","credit side",
        "cr side","in","incoming",
    ],
    "balance": [
        "balance","running balance","closing balance","ledger balance",
        "available balance","book balance","bal","end balance",
        "balance (ngn)","bal (ngn)","current balance",
    ],
    "reference": [
        "reference","ref","ref no","reference no","reference number",
        "transaction ref","trn ref","txn ref","cheque no","cheque number",
        "instrument no","session id","transaction id","trans id",
        "trace no","trace id","tran id","tran ref","chq no",
    ],
    "bank_account": [
        "bank account","account","account name","account number",
        "bank account name","bank acc","bank a/c","a/c","a/c number",
        "account no","acct","acct no","acct name","account_no",
    ],
}

_MATCH_THRESHOLD = 0.52


# ================================================================== #
#  MAIN ENTRY                                                          #
# ================================================================== #

def parse_file(doc) -> list[dict]:
    if not doc.upload_file:
        frappe.throw(
            "No file attached. Please attach an Excel, CSV, OFX or MT940 file."
        )

    file_path = _resolve_file_path(doc.upload_file)
    file_type = _detect_file_type(doc.upload_file, getattr(doc, "file_type", "") or "")
    file_type = _sniff_true_file_type(file_path, file_type)

    frappe.logger().info(f"[BSU] Parsing {file_type} from {file_path}")

    try:
        if file_type in ("XLSX", "XLS", "XLSB"):
            rows = _parse_excel(file_path, doc)
        elif file_type == "CSV":
            rows = _parse_csv(file_path, doc)
        elif file_type == "OFX":
            rows = _parse_ofx(file_path)
        elif file_type == "MT940":
            rows = _parse_mt940(file_path)
        else:
            frappe.throw(f"Unsupported file type '{file_type}'. Supported: CSV, XLSX, XLS, OFX, MT940.")
    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Bank Statement Upload — parse error")
        frappe.throw(f"Error reading file: {e}")

    if not rows:
        frappe.throw(
            "No data rows extracted.\n"
            "• Confirm the Date and Description column names match the Column Mapping.\n"
            "• Check Header Row number (default = 1).\n"
            "• Ensure at least one row has a non-zero Debit or Credit amount."
        )

    frappe.logger().info(f"[BSU] Extracted {len(rows)} rows. First: {rows[0]}")
    return rows


# ================================================================== #
#  FILE PATH RESOLUTION                                                #
# ================================================================== #

def _resolve_file_path(file_url: str) -> str:
    from urllib.parse import unquote
    file_url = unquote(str(file_url))
    site_path = frappe.get_site_path()

    if os.path.isabs(file_url) and os.path.exists(file_url):
        return file_url

    clean = file_url.split("?")[0].rstrip("/")

    if clean.startswith("/private/files/"):
        fname = clean[len("/private/files/"):]
        candidates = [os.path.join(site_path, "private", "files", fname)]
    elif clean.startswith("/files/"):
        fname = clean[len("/files/"):]
        candidates = [
            os.path.join(site_path, "public",  "files", fname),
            os.path.join(site_path, "private", "files", fname),
        ]
    else:
        fname = os.path.basename(clean)
        candidates = [
            os.path.join(site_path, "public",  "files", fname),
            os.path.join(site_path, "private", "files", fname),
            clean,
            os.path.join(site_path, clean.lstrip("/")),
        ]

    for p in candidates:
        if p and os.path.exists(p):
            return p

    # File doctype lookup
    row = frappe.db.get_value("File", {"file_url": file_url},
                               ["file_url", "is_private"], as_dict=True)
    if row:
        sub = "private" if row.is_private else "public"
        p = os.path.join(site_path, sub, row.file_url.lstrip("/"))
        if os.path.exists(p):
            return p

    frappe.throw(
        f"Cannot locate uploaded file on disk: {file_url}\n"
        "Re-attach the file and try again."
    )


def _detect_file_type(file_url: str, declared: str) -> str:
    if declared and declared.upper() in ("CSV","XLSX","XLS","OFX","MT940"):
        return declared.upper()
    ext = os.path.splitext(str(file_url).split("?")[0])[1].lower().lstrip(".")
    mapping = {"csv":"CSV","xlsx":"XLSX","xls":"XLS","ofx":"OFX",
               "qfx":"OFX","sta":"MT940","940":"MT940","txt":"CSV"}
    detected = mapping.get(ext)
    if not detected:
        frappe.throw(f"Cannot determine file type from '.{ext}'. Set the File Type field manually.")
    return detected


def _sniff_true_file_type(file_path: str, hint: str) -> str:
    try:
        with open(file_path, "rb") as f:
            magic = f.read(8)
    except OSError:
        return hint
    if magic[:2] == b"PK":
        return "XLSX"
    if magic[:8] == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1":
        return "XLS"
    if magic[:5].lower() in (b"<html", b"<!doc"):
        frappe.throw(
            "The file is an HTML page with an .xlsx extension.\n"
            "Open in Excel → Save As → Excel Workbook (.xlsx) → re-upload."
        )
    return hint


# ================================================================== #
#  EXCEL — three-engine waterfall                                      #
# ================================================================== #

def _parse_excel(file_path: str, doc) -> list[dict]:
    errors = []

    for engine_fn in (_try_openpyxl, _try_xlrd, _try_pandas):
        try:
            result = engine_fn(file_path, doc)
            if result is not None:
                return result
        except Exception as e:
            errors.append(f"{engine_fn.__name__}: {e}")
            frappe.logger().warning(f"[BSU] {engine_fn.__name__} failed: {e}")

    frappe.log_error("\n".join(errors), "Bank Statement Upload — Excel engines failed")
    frappe.throw(
        "Could not open the Excel file.\n"
        + "\n".join(f"• {e}" for e in errors)
        + "\nTip: open in Excel/LibreOffice, Save As .xlsx, re-upload."
    )


def _try_openpyxl(file_path, doc):
    import openpyxl
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    sname = getattr(doc, "sheet_name", None)
    ws = wb[sname] if (sname and sname in wb.sheetnames) else wb[wb.sheetnames[0]]
    all_rows = [[_openpyxl_cell(c) for c in row] for row in ws.iter_rows()]
    wb.close()
    return _process_rows(all_rows, doc)


def _try_xlrd(file_path, doc):
    import xlrd
    wb = xlrd.open_workbook(file_path)
    sname = getattr(doc, "sheet_name", None)
    ws = (wb.sheet_by_name(sname) if (sname and sname in wb.sheet_names())
          else wb.sheet_by_index(0))
    all_rows = []
    for r in range(ws.nrows):
        row_vals = []
        for c in range(ws.ncols):
            cell = ws.cell(r, c)
            if cell.ctype == 3:  # date
                try:
                    row_vals.append(
                        xlrd.xldate_as_datetime(cell.value, wb.datemode).strftime("%Y-%m-%d")
                    )
                except Exception:
                    row_vals.append(str(cell.value))
            elif cell.ctype == 2:  # number
                row_vals.append(cell.value)
            else:
                row_vals.append(cell.value)
        all_rows.append(row_vals)
    return _process_rows(all_rows, doc)


def _try_pandas(file_path, doc):
    import pandas as pd
    sname = getattr(doc, "sheet_name", None) or 0
    hdr   = _cint(getattr(doc, "header_row", None) or 1) - 1
    df    = None
    for eng in ("openpyxl", "xlrd"):
        try:
            df = pd.read_excel(file_path, sheet_name=sname,
                               header=hdr, dtype=str, engine=eng)
            break
        except Exception:
            continue
    if df is None:
        raise RuntimeError("pandas could not open file")
    headers   = [str(c) for c in df.columns]
    data_rows = [[str(v).strip() if v is not None else ""
                  for v in row] for row in df.fillna("").values.tolist()]
    # Insert fake header row so _process_rows can extract it
    all_rows = [headers] + data_rows
    doc_with_hdr1 = _DocProxy(doc, header_row=1)
    return _process_rows(all_rows, doc_with_hdr1)


class _DocProxy:
    """Thin wrapper that overrides specific fields on doc for _process_rows."""
    def __init__(self, doc, **overrides):
        self._doc = doc
        self._ov  = overrides
    def __getattr__(self, name):
        if name in self._ov:
            return self._ov[name]
        return getattr(self._doc, name)
    def get(self, name, default=None):
        if name in self._ov:
            return self._ov[name]
        return self._doc.get(name, default) if hasattr(self._doc, 'get') else getattr(self._doc, name, default)


def _openpyxl_cell(cell):
    from datetime import date, datetime as dt
    if cell.value is None:
        return None
    if isinstance(cell.value, (date, dt)):
        return cell.value.strftime("%Y-%m-%d")
    return cell.value


def _process_rows(all_rows: list, doc) -> list[dict]:
    if not all_rows:
        frappe.throw("Excel file is empty.")
    hdr_idx = _cint(getattr(doc, "header_row", None) or 1) - 1
    if len(all_rows) <= hdr_idx:
        frappe.throw(f"Header row {hdr_idx+1} not found — file has {len(all_rows)} row(s).")
    headers   = [str(h).strip() if h is not None else "" for h in all_rows[hdr_idx]]
    data_rows = all_rows[hdr_idx + 1:]
    if not any(any(c for c in r) for r in data_rows):
        frappe.throw("No data rows found after the header row.")
    num_fmt = _detect_number_format(data_rows)
    col_map = _build_column_map(headers, doc)
    frappe.logger().info(f"[BSU] headers={headers} col_map={col_map} num_fmt={num_fmt}")
    return _extract_rows(data_rows, col_map, doc, num_fmt)


# ================================================================== #
#  CSV                                                                 #
# ================================================================== #

def _parse_csv(file_path: str, doc) -> list[dict]:
    import csv
    content = _read_encoded(file_path)
    try:
        dialect = csv.Sniffer().sniff(content[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    all_rows = list(csv.reader(content.splitlines(), dialect))
    if not all_rows:
        frappe.throw("CSV file is empty.")
    hdr_idx   = _cint(getattr(doc, "header_row", None) or 1) - 1
    headers   = [h.strip() for h in all_rows[hdr_idx]]
    data_rows = [r for r in all_rows[hdr_idx+1:] if any(c.strip() for c in r)]
    num_fmt   = _detect_number_format(data_rows)
    col_map   = _build_column_map(headers, doc)
    frappe.logger().info(f"[BSU CSV] headers={headers} col_map={col_map}")
    return _extract_rows(data_rows, col_map, doc, num_fmt)


def _read_encoded(path: str) -> str:
    for enc in ("utf-8-sig","utf-8","latin-1","cp1252","iso-8859-1"):
        try:
            with open(path,"r",encoding=enc,errors="strict") as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    with open(path,"r",encoding="utf-8",errors="replace") as f:
        return f.read()


# ================================================================== #
#  ML: NUMBER FORMAT DETECTION                                         #
# ================================================================== #

def _detect_number_format(data_rows: list) -> str:
    us_votes = eu_votes = 0
    for row in data_rows[:60]:
        for cell in row:
            if cell is None:
                continue
            s = re.sub(r'[₦$€£\s]', '', str(cell)).strip()
            if re.match(r'^\-?\d{1,3}(,\d{3})+\.\d+$', s):
                us_votes += 1
            elif re.match(r'^\-?\d{1,3}(\.\d{3})+,\d+$', s):
                eu_votes += 1
    fmt = "eu" if eu_votes > us_votes else "us"
    frappe.logger().info(f"[BSU] Number format: {fmt} (us={us_votes}, eu={eu_votes})")
    return fmt


# ================================================================== #
#  ML: COLUMN HEADER MATCHING                                          #
# ================================================================== #

def _fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _score_header(header: str, vocab: list) -> float:
    h = header.lower().strip()
    if not h:
        return 0.0
    best = 0.0
    for term in vocab:
        s = (0.85 + 0.15 * len(term) / max(len(h), len(term))
             if (term in h or h in term)
             else _fuzzy(h, term))
        if s > best:
            best = s
    return best


def _build_column_map(headers: list, doc) -> dict:
    """Two-tier: user config first, ML fill-in for missing."""

    def resolve(ref):
        if not ref:
            return None
        ref = str(ref).strip()
        # Column letter (A, B, AA…)
        if re.match(r'^[A-Za-z]{1,3}$', ref):
            idx = 0
            for ch in ref.upper():
                idx = idx * 26 + (ord(ch) - 64)
            idx -= 1
            return idx if idx < len(headers) else None
        # Exact match
        for i, h in enumerate(headers):
            if h.lower() == ref.lower():
                return i
        # Fuzzy match on user-provided ref vs actual headers
        best_s, best_i = 0.0, None
        for i, h in enumerate(headers):
            s = _fuzzy(ref, h)
            if s > best_s:
                best_s, best_i = s, i
        return best_i if best_s >= _MATCH_THRESHOLD else None

    col_map = {
        "date":         resolve(doc.date_column),
        "narration":    resolve(doc.narration_column),
        "debit":        resolve(doc.debit_column),
        "credit":       resolve(doc.credit_column),
        "bank_account": resolve(doc.get("bank_account_column")),
        "reference":    resolve(doc.get("reference_column")),
        "balance":      resolve(doc.get("balance_column")),
    }

    # ML fill-in for anything still None
    missing = [f for f, v in col_map.items() if v is None]
    if missing:
        claimed = {v for v in col_map.values() if v is not None}
        scores  = {}
        for f in missing:
            ranked = sorted(
                ((c, _score_header(headers[c], _COL_VOCAB.get(f, [])))
                 for c in range(len(headers)) if c not in claimed),
                key=lambda x: -x[1]
            )
            scores[f] = ranked

        # Greedy assignment highest-confidence first
        for f in sorted(missing, key=lambda f: scores[f][0][1] if scores[f] else 0, reverse=True):
            for col_idx, score in scores[f]:
                if score >= _MATCH_THRESHOLD and col_idx not in claimed:
                    col_map[f] = col_idx
                    claimed.add(col_idx)
                    frappe.logger().info(
                        f"[BSU ML] Auto-mapped '{headers[col_idx]}' → {f} (score={score:.2f})"
                    )
                    break

    _validate_col_map(col_map, headers, doc)
    return col_map


def _validate_col_map(col_map, headers, doc):
    h_str = ", ".join(h for h in headers if h)
    if col_map["date"] is None:
        frappe.throw(
            f"Date column not found. Configured: '{doc.date_column}'.\n"
            f"File headers: {h_str}"
        )
    if col_map["narration"] is None:
        frappe.throw(
            f"Description column not found. Configured: '{doc.narration_column}'.\n"
            f"File headers: {h_str}"
        )
    if col_map["debit"] is None and col_map["credit"] is None:
        frappe.throw(
            "No Debit or Credit column found.\n"
            "Tip: single signed-amount column → set as Debit column.\n"
            f"File headers: {h_str}"
        )


# ================================================================== #
#  ROW EXTRACTION                                                      #
# ================================================================== #

def _extract_rows(data_rows, col_map, doc, num_fmt="us") -> list[dict]:
    rows = []
    default_bank = doc.get("default_bank_account") or ""

    for row_idx, row in enumerate(data_rows, start=1):
        row = list(row)

        def cell(key):
            idx = col_map.get(key)
            if idx is None or idx >= len(row):
                return None
            v = row[idx]
            return None if v is None else str(v).strip()

        date_raw    = cell("date")
        narration   = cell("narration") or ""
        debit_raw   = cell("debit")
        credit_raw  = cell("credit")
        bank_raw    = cell("bank_account") or default_bank
        ref_raw     = cell("reference")   or ""
        balance_raw = cell("balance")

        if not any([date_raw, narration, debit_raw, credit_raw]):
            continue

        # Skip repeated header rows mid-file
        if date_raw and date_raw.lower() in _COL_VOCAB["date"]:
            continue

        parsed_date = _parse_date(date_raw)
        if not parsed_date:
            frappe.logger().warning(f"[BSU] Row {row_idx}: unparseable date '{date_raw}' — skipped")
            continue

        debit  = _clean_amount(debit_raw,  num_fmt)
        credit = _clean_amount(credit_raw, num_fmt)

        # Single signed-amount column
        if col_map.get("credit") is None and debit_raw:
            signed = _clean_amount(debit_raw, num_fmt, allow_negative=True)
            debit, credit = (abs(signed), 0.0) if signed < 0 else (0.0, signed)
        elif debit == 0.0 and credit == 0.0 and debit_raw:
            signed = _clean_amount(debit_raw, num_fmt, allow_negative=True)
            if signed < 0:
                debit = abs(signed)
            elif signed > 0:
                credit = signed

        if debit == 0.0 and credit == 0.0:
            continue

        currency, fx_hint = _detect_currency(narration)

        rows.append({
            "row_number":       row_idx,
            "transaction_date": parsed_date,
            "raw_narration":    narration[:500],
            "debit_amount":     debit,
            "credit_amount":    credit,
            "bank_account_raw": bank_raw,
            "reference_no":     ref_raw[:140],
            "running_balance":  _clean_amount(balance_raw, num_fmt),
            "payment_currency": currency,
            "fx_hint":          fx_hint,
        })

    return rows


# ================================================================== #
#  OFX                                                                 #
# ================================================================== #

def _parse_ofx(file_path: str) -> list[dict]:
    content = _read_encoded(file_path)
    txns    = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', content, re.DOTALL|re.IGNORECASE)
    if not txns:
        frappe.throw("No transactions found in OFX file.")
    rows = []
    for idx, txn in enumerate(txns, start=1):
        def tag(name, _t=txn):
            m = re.search(rf'<{name}>\s*(.*?)(?:\s*<|$)', _t, re.IGNORECASE)
            return m.group(1).strip() if m else ""
        parsed_date = _parse_date(tag("DTPOSTED")[:8])
        amount      = _clean_amount(tag("TRNAMT"), "us", allow_negative=True)
        narration   = tag("MEMO") or tag("NAME") or ""
        debit  = abs(amount) if amount < 0 else 0.0
        credit = amount      if amount > 0 else 0.0
        if debit == 0.0 and credit == 0.0:
            continue
        currency, fx_hint = _detect_currency(narration)
        rows.append({
            "row_number":       idx,
            "transaction_date": parsed_date,
            "raw_narration":    narration[:500],
            "debit_amount":     debit,
            "credit_amount":    credit,
            "bank_account_raw": tag("ACCTID"),
            "reference_no":     tag("FITID")[:140],
            "running_balance":  0.0,
            "payment_currency": currency,
            "fx_hint":          fx_hint,
        })
    return rows


# ================================================================== #
#  MT940                                                               #
# ================================================================== #

def _parse_mt940(file_path: str) -> list[dict]:
    content = _read_encoded(file_path)
    acct_m  = re.search(r':25:(.*?)[\r\n]', content)
    acct    = acct_m.group(1).strip() if acct_m else ""
    pattern = re.compile(
        r':61:(\d{6})\d{0,4}([CD])(\d+,\d+)(?:N\w+)?(.*?)(?=:61:|:62[FM]:|$)',
        re.DOTALL
    )
    rows = []
    for idx, m in enumerate(pattern.finditer(content), start=1):
        parsed_date = _parse_date("20" + m.group(1))
        try:
            amount = float(m.group(3).replace(",", "."))
        except ValueError:
            continue
        is_debit  = m.group(2).upper() == "D"
        narration = re.sub(r'\s+', ' ', m.group(4)).strip()[:500]
        currency, fx_hint = _detect_currency(narration)
        rows.append({
            "row_number":       idx,
            "transaction_date": parsed_date,
            "raw_narration":    narration,
            "debit_amount":     amount if is_debit     else 0.0,
            "credit_amount":    amount if not is_debit else 0.0,
            "bank_account_raw": acct,
            "reference_no":     "",
            "running_balance":  0.0,
            "payment_currency": currency,
            "fx_hint":          fx_hint,
        })
    return rows


# ================================================================== #
#  DATE PARSING                                                        #
# ================================================================== #

_DATE_FMTS = [
    "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S", "%Y%m%d%H%M%S",
    "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y",
    "%d.%m.%Y", "%Y%m%d",
    "%d/%m/%y", "%m/%d/%y", "%d-%m-%y",
    "%d %b %Y", "%d-%b-%Y", "%d %B %Y",
    "%d-%b-%y", "%d %b %y",
]


def _parse_date(raw) -> str | None:
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return None

    # Already ISO
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
        return raw

    # Excel serial
    try:
        serial = float(raw)
        if 10000 < serial < 120000:
            import datetime as _dt
            return (_dt.timedelta(days=int(serial))
                    + _dt.datetime(1899, 12, 30)).strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        pass

    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw[:20], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Digit extraction fallback
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 8:
        for fmt in ("%Y%m%d", "%d%m%Y"):
            try:
                return datetime.strptime(digits, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

    return None


# ================================================================== #
#  AMOUNT PARSING                                                      #
# ================================================================== #

def _clean_amount(raw, num_fmt="us", allow_negative=False) -> float:
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        v = float(raw)
        return v if allow_negative else abs(v)
    s = str(raw).strip()
    if not s:
        return 0.0

    # Parenthesised negative: (500.00)
    is_paren = bool(re.match(r'^\(.*\)$', s))
    s = s.strip("()")

    # Remove currency symbols and markers
    s = re.sub(r'[₦$€£¥₵₹]', '', s)
    s = re.sub(r'(?i)\s*(dr|cr|ngn|usd|gbp|eur|ghs|kes|zar)\s*', '', s).strip()

    if num_fmt == "eu":
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")

    s = re.sub(r"[^\d.\-]", "", s)
    if not s or s in ("-", "."):
        return 0.0

    try:
        v = float(s)
    except ValueError:
        return 0.0

    if is_paren:
        v = -abs(v)

    return v if allow_negative else abs(v)


# ================================================================== #
#  CURRENCY DETECTION                                                  #
# ================================================================== #

_CURRENCIES = [
    ("USD", r"\bUSD\b|US\s?DOLLAR|SWIFT|MT103|\$"),
    ("GBP", r"\bGBP\b|STERLING|POUNDS?|£"),
    ("EUR", r"\bEUR\b|EURO|€"),
    ("GHS", r"\bGHS\b|CEDI|₵"),
    ("KES", r"\bKES\b|SHILLING"),
    ("ZAR", r"\bZAR\b|RAND"),
    ("XOF", r"\bXOF\b|FCFA"),
    ("EGP", r"\bEGP\b|EGYPTIAN POUND"),
    ("ZMW", r"\bZMW\b|KWACHA"),
    ("TZS", r"\bTZS\b|TANZANIAN SHILLING"),
    ("UGX", r"\bUGX\b|UGANDAN SHILLING"),
    ("CNY", r"\bCNY\b|\bRMB\b|YUAN"),
    ("AED", r"\bAED\b|DIRHAM"),
    ("INR", r"\bINR\b|RUPEE|₹"),
]


def _detect_currency(narration: str):
    for code, pat in _CURRENCIES:
        if re.search(pat, narration, re.IGNORECASE):
            return code, code
    return "NGN", None


# ================================================================== #
#  BANK ACCOUNT ML MATCHER (called from ai_coder)                     #
# ================================================================== #

def match_bank_account(raw: str, company: str) -> str | None:
    if not raw:
        return None
    raw = str(raw).strip()

    # Exact name
    hit = frappe.db.get_value("Bank Account", {"account_name": raw}, "name")
    if hit:
        return hit

    # Exact account number
    hit = frappe.db.get_value("Bank Account", {"bank_account_no": raw}, "name")
    if hit:
        return hit

    # Digit suffix match (last 6 digits of account number)
    digits = re.sub(r'\D', '', raw)
    if len(digits) >= 6:
        hit = frappe.db.sql(
            "SELECT name FROM `tabBank Account` "
            "WHERE bank_account_no LIKE %s LIMIT 1",
            f"%{digits[-6:]}"
        )
        if hit:
            return hit[0][0]

    # Fuzzy match
    accounts = frappe.get_all(
        "Bank Account",
        fields=["name","account_name","bank_account_no","bank"],
    )
    raw_toks   = set(re.findall(r'\w+', raw.lower()))
    raw_digits = set(re.findall(r'\d{4,}', raw))
    best_s, best_n = 0.0, None

    for a in accounts:
        s = _fuzzy(raw, a.account_name or "")
        # Token overlap
        a_toks = set(re.findall(r'\w+', (a.account_name or "").lower()))
        if raw_toks and a_toks:
            s = max(s, len(raw_toks & a_toks) / len(raw_toks | a_toks) * 0.9)
        # Digit overlap
        a_digits = set(re.findall(r'\d{4,}', a.bank_account_no or ""))
        if raw_digits and a_digits and raw_digits & a_digits:
            s = max(s, 0.95)
        if s > best_s:
            best_s, best_n = s, a.name

    if best_s >= 0.60:
        frappe.logger().info(f"[BSU] match_bank_account '{raw}' → '{best_n}' ({best_s:.2f})")
        return best_n

    return None


# ================================================================== #
#  UTILITIES                                                           #
# ================================================================== #

def _cint(v, default=0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default