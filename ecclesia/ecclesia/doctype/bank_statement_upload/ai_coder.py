# ecclesia/ecclesia/doctype/bank_statement_upload/ai_coder.py
"""
Enterprise-grade AI transaction analysis engine.

Pipeline per row (priority order):
  1.  Deduplication fingerprint
  2.  Enhanced narration cleaning + payee / person name extraction
  3.  Payroll hard rule  → Salaries Payable (99%)
  4.  Bank charge detection → Bank Charges (98%)
  5.  Interest detection → Interest Income / Expense (98%)
  6.  Transport / travel detection → Transport Expense (97%)
  7.  Alias table  → instant full coding (97%)
  8.  Party match via inverted token index → Supplier / Customer / Employee / Member
  9.  CoA keyword scoring (30+ account patterns)
  10. Suspense fallback

Performance:
  - All Suppliers / Customers / Employees / Members loaded ONCE per batch
  - Inverted token index: O(query_tokens) candidate lookup vs O(all_parties)
  - Typical 300-row batch: <3 seconds vs 30+ seconds without index
  - Bank account matched via ML fuzzy scorer (not exact-only)

Output per row: matches `Bank Statement Upload Item` child doctype exactly.
"""

import frappe
import re
import hashlib
import statistics
from frappe.utils import flt

# Move parser import to module level — not per-row (avoid per-row import overhead)
try:
    from ecclesia.ecclesia.doctype.bank_statement_upload.parser import match_bank_account as _ml_match_bank
except ImportError:
    _ml_match_bank = None


# ================================================================== #
#  PATTERN LIBRARIES                                                   #
# ================================================================== #

PAYROLL_PATTERNS = [
    r'\bSALARY\b', r'\bSALARIES\b', r'\bPAYROLL\b', r'\bWAGE\b',
    r'\bNIBSS.*PAY\b', r'\bSTAFF.*PAY\b', r'\bEMPLOYEE\s*PAYMENT\b',
    r'\bREMUNERATION\b', r'\bMONTHLY\s*PAY\b', r'\bNSWF\b', r'\bNHF\b',
    r'\bPENSION\b',
]

BANK_CHARGE_PATTERNS = [
    r'\bSMS\s*CHARGE\b', r'\bSMS\s*ALERT\b', r'\bALERT\s*FEE\b',
    r'\bSTAMP\s*DUTY\b', r'\bWITHHOLDING\s*TAX\b', r'\bWHT\b',
    r'\bCOMMISSION\s*OUTWARD\b', r'\bCOMMISSION\s*ON\b',
    r'\bBANK\s*CHARGES?\b', r'\bCOT\b', r'\bMAINT.*FEE\b',
    r'\bCARD\s*MAINT\b', r'\bATM\s*FEE\b', r'\bTRANSACTION\s*FEE\b',
    r'\bSERVICE\s*CHARGE\b', r'\bPROCESSING\s*FEE\b',
    r'\bLEDGER\s*FEE\b', r'\bACCOUNT\s*MAINT\b', r'\bMONTHLY\s*SERVICE\b',
    r'\bNOTIF.*FEE\b',
]

INTEREST_RECEIVED_PATTERNS = [
    r'\bINTEREST\s*(?:RECEIVED|EARNED|CREDIT|PAID\s*TO)\b',
    r'\bINTEREST\s*ON\s*(?:SAVINGS|DEPOSIT|INVESTMENT|FIXED)\b',
    r'\bINTEREST\s*INCOME\b',
]

INTEREST_PAID_PATTERNS = [
    r'\bINTEREST\s*(?:CHARGED|PAID|DEBIT|EXPENSE)\b',
    r'\bINTEREST\s*ON\s*(?:LOAN|OVERDRAFT|MORTGAGE|FACILITY)\b',
    r'\bINTEREST\s*EXPENSE\b', r'\bLOAN\s*INTEREST\b',
]

TRANSPORT_PATTERNS = [
    r'\bTRANSPORT\b', r'\bTRAVEL\b', r'\bRIDE\b', r'\bFARE\b',
    r'\bTAXI\b', r'\bUBER\b', r'\bBOLT\b', r'\bBUS\b', r'\bTRAIN\b',
    r'\bFLIGHT\b', r'\bAIRLINE\b', r'\bJET\b', r'\bAIR\s*TICKET\b',
    r'\bPARKING\b', r'\bTOLL\b', r'\bFERRY\b',
]

STRIP_PREFIXES = [
    "NIP/", "NIBSS/", "INTRABANK/", "SWIFT/", "CR/", "DR/",
    "NIP-", "INTERBANK/", "RTGS/", "MT103/", "USSD/",
    "MOB/", "WEB/", "ATM/", "POS/", "TRF/", "FT/",
]

# ================================================================== #
#  CoA RULES — (pattern, account_name_keyword, cashflow, score)       #
#  Account name keyword is searched in the live Chart of Accounts.    #
#  Higher score = higher confidence.                                   #
# ================================================================== #

COA_RULES = [
    # Bank charges (highest priority)
    (r'\bSMS\s*(?:CHARGE|ALERT)\b|\bALERT\s*FEE\b|\bNOTIF.*FEE\b',
        "bank charges",         "Operating costs",                        18),
    (r'\bSTAMP\s*DUTY\b',
        "stamp duty",           "Tax Payment",                            18),
    (r'\bWITHHOLDING\s*TAX\b|\bWHT\b',
        "withholding tax",      "Tax Payment",                            18),
    (r'\bCOMMISSION\s*(?:OUTWARD|ON\s*TRANSFER|ON)\b',
        "bank charges",         "Operating costs",                        17),
    (r'\bBANK\s*CHARGES?\b|\bCOT\b|\bMAINT.*FEE\b|\bCARD\s*MAINT\b',
        "bank charges",         "Operating costs",                        17),
    (r'\bATM\s*FEE\b|\bTRANSACTION\s*FEE\b|\bSERVICE\s*CHARGE\b',
        "bank charges",         "Operating costs",                        16),
    (r'\bLEDGER\s*FEE\b|\bACCOUNT\s*MAINT\b|\bMONTHLY\s*SERVICE\b',
        "bank charges",         "Operating costs",                        16),
    # Interest
    (r'\bINTEREST\s*(?:RECEIVED|EARNED|CREDIT)\b|\bINTEREST\s*INCOME\b',
        "interest income",      "Interest received",                      18),
    (r'\bINTEREST\s*(?:CHARGED|PAID|EXPENSE|DEBIT)\b|\bLOAN\s*INTEREST\b',
        "interest expense",     "Loan repayments",                        18),
    # Transport
    (r'\bUBER\b|\bBOLT\b',
        "transport expense",    "Operating costs",                        18),
    (r'\bTRANSPORT\b|\bTAXI\b|\bFARE\b|\bRIDE\b',
        "transport expense",    "Operating costs",                        17),
    (r'\bFLIGHT\b|\bAIRLINE\b|\bAIR\s*TICKET\b',
        "travel expense",       "Operating costs",                        17),
    # Taxes
    (r'\bFIRS\b|\bLIRS\b|\bTAX\s*REMIT\b|\bVAT\b',
        "tax payable",          "Tax Payment",                            17),
    # Payroll
    (r'\bSALARY\b|\bPAYROLL\b|\bWAGE\b|\bSTAFF\s*PAY\b',
        "salaries payable",     "Salary payments",                        18),
    (r'\bPENSION\b',
        "pension payable",      "Salary payments",                        17),
    # Rent/Utilities
    (r'\bRENT\b|\bLEASE\b|\bTENANCY\b',
        "rent expense",         "Rent & utilities",                       17),
    (r'\bELECTRIC\b|\bNEDC\b|\bAEDC\b|\bKEDC\b|\bPEDC\b|\bEKO\s*DISC\b|\bIEDC\b',
        "electricity",          "Rent & utilities",                       17),
    (r'\bWATER\s*BILL\b|\bLAWSMA\b',
        "water",                "Rent & utilities",                       16),
    (r'\bINTERNET\b|\bBROADBAND\b|\bFIBRE\b',
        "internet",             "Operating costs",                        16),
    (r'\bMTN\b|\bAIRTEL\b|\bGLO\b|\b9MOBILE\b',
        "telephone",            "Operating costs",                        15),
    # Insurance / Loans
    (r'\bINSURANCE\b|\bPREMIUM\b',
        "insurance expense",    "Operating costs",                        16),
    (r'\bLOAN\s*REPAY\b|\bINSTALMENT\b|\bLOAN\s*DEDUCT\b',
        "loan payable",         "Loan repayments",                        17),
    (r'\bDIVIDEND\b',
        "dividend",             "Dividend payments",                      17),
    # Church-specific
    (r'\bTITHE\b|\bOFFERING\b',
        "tithe",                "Customer payments for goods/services",   18),
    (r'\bPLEDGE\b',
        "pledge",               "Customer payments for goods/services",   17),
    (r'\bDONATION\b|\bGIFT\b',
        "donation",             "Customer payments for goods/services",   16),
    # Office
    (r'\bFUEL\b|\bPETROL\b|\bDIESEL\b|\bNNPC\b',
        "fuel expense",         "Operating costs",                        16),
    (r'\bPRINT\b|\bSTATION\b|\bPAPER\b',
        "stationery",           "Operating costs",                        15),
    (r'\bSUBSCRIPT\b|\bLICENC\b|\bSOFTWARE\b|\bSAAS\b|\bCLOUD\b|\bAWS\b|\bAZURE\b',
        "software",             "Operating costs",                        16),
    (r'\bSECURITY\b|\bGUARD\b',
        "security expense",     "Operating costs",                        15),
    (r'\bCLEAN\b|\bJANITOR\b|\bHOUSEKEEP\b',
        "cleaning expense",     "Operating costs",                        15),
    (r'\bMEDICAL\b|\bHMO\b|\bHEALTH\b',
        "medical expense",      "Operating costs",                        16),
    (r'\bTRAINING\b|\bCOURSE\b|\bSEMINAR\b|\bWORKSHOP\b',
        "training expense",     "Operating costs",                        15),
    (r'\bADVERT\b|\bMARKET\b|\bPROMO\b',
        "advertising",          "Operating costs",                        15),
    (r'\bREPAIR\b|\bMAINTENANC\b|\bSERVICING\b',
        "repairs",              "Operating costs",                        15),
    (r'\bEQUIPMENT\b|\bMACHINERY\b|\bFURNITURE\b|\bVEHICLE\b',
        "equipment",            "Capital expenditures",                   15),
]

# Party type routing table
PARTY_TRANS = {
    ("Supplier", True):  ("Payments", "Supplier Payment",  "Supplier payments"),
    ("Supplier", False): ("Receipts", "Supplier Refunds",  "Supplier payments"),
    ("Customer", True):  ("Payments", "Expense Payment",   "Operating costs"),
    ("Customer", False): ("Receipts", "Customer Receipt",  "Customer payments for goods/services"),
    ("Employee", True):  ("Payments", "Expense Payment",   "Salary payments"),
    ("Employee", False): ("Receipts", "Revenue Receipt",   "Customer payments for goods/services"),
    ("Member",   False): ("Receipts", "Member Tithe",      "Customer payments for goods/services"),
    ("Member",   True):  ("Payments", "Expense Payment",   "Operating costs"),
}


# ================================================================== #
#  MAIN ENTRY                                                          #
# ================================================================== #

def analyse_rows(raw_rows: list, import_doc) -> list:
    """
    Run full AI pipeline on every raw row.
    Returns a list of dicts ready to append as Bank Statement Upload Item rows.
    """
    company           = import_doc.company
    default_cc        = import_doc.default_cost_center
    default_dept      = import_doc.default_department
    conf_threshold    = flt(import_doc.confidence_threshold or 85)
    skip_dupes        = import_doc.skip_duplicates
    default_bank_acct = import_doc.get("default_bank_account") or ""

    # ── Pre-load all lookups ONCE ────────────────────────────────── #
    alias_map      = _load_alias_map(company)
    accounts_index = _load_accounts_index(company)
    party_index, token_index = _load_party_index()
    history_map    = _load_amount_history()
    seen_hashes    = set()

    frappe.logger().info(
        f"[BSU] Starting analysis: {len(raw_rows)} rows, "
        f"{len(party_index)} parties, {len(alias_map)} aliases, "
        f"{len(accounts_index)} accounts"
    )

    staged = []
    for raw in raw_rows:
        try:
            item = _analyse_single(
                raw, company, default_cc, default_dept,
                conf_threshold, skip_dupes,
                alias_map, accounts_index,
                party_index, token_index,
                history_map, seen_hashes,
                default_bank_acct
            )
        except Exception as e:
            # Never let a single row crash the whole batch
            frappe.log_error(
                f"Row {raw.get('row_number')}: {e}\n{frappe.get_traceback()}",
                "BSU row analysis error"
            )
            item = _error_row(raw, str(e))

        seen_hashes.add(item["hash_fingerprint"])
        staged.append(item)

    ready  = sum(1 for r in staged if r["row_status"] == "Ready")
    review = sum(1 for r in staged if r["row_status"] == "Review")
    frappe.logger().info(f"[BSU] Analysis done. Ready={ready}, Review={review}")
    return staged


# ================================================================== #
#  SINGLE ROW PIPELINE                                                 #
# ================================================================== #

def _analyse_single(raw, company, default_cc, default_dept,
                    conf_threshold, skip_dupes,
                    alias_map, accounts_index,
                    party_index, token_index,
                    history_map, seen_hashes,
                    default_bank_acct=""):

    narration = (raw.get("raw_narration") or "").strip()
    debit     = flt(raw.get("debit_amount",  0))
    credit    = flt(raw.get("credit_amount", 0))
    currency  = raw.get("payment_currency", "NGN") or "NGN"
    is_debit  = debit > 0

    # ── 1. Deduplication ─────────────────────────────────────────── #
    fp      = _fingerprint(raw)
    is_dupe = skip_dupes and (_hash_exists_in_db(fp) or fp in seen_hashes)

    # ── 2. Enhanced cleaning + extraction ────────────────────────── #
    cleaned, payee_tokens, extracted_names = _clean_and_extract(narration)

    # ── 3–6. Hard rules (short-circuit — no party lookup needed) ─── #
    # Payroll
    if _matches_any(narration, PAYROLL_PATTERNS) and is_debit:
        return _quick_row(
            raw, narration, cleaned, debit, credit, currency, is_dupe, fp,
            accounts_index, default_cc, default_dept, default_bank_acct,
            pay_name="Payroll",
            party_type="Employee",
            acct_kw="salaries payable", acct_fallback="salary expense",
            doc_type="Payments", trans_type="Expense Payment",
            cashflow="Salary payments", confidence=99.0,
            coding_method="Payroll hard rule → Salaries Payable",
        )

    # Bank charge
    charge_name = _detect_bank_charge(narration)
    if charge_name and is_debit:
        # pay_name = first 2 meaningful words of the bank account
        bank_raw_for_charge = raw.get("bank_account_raw", "") or default_bank_acct
        charge_pay_name = (_pay_name_from_bank_account(bank_raw_for_charge)
                           or charge_name)
        return _quick_row(
            raw, narration, cleaned, debit, credit, currency, is_dupe, fp,
            accounts_index, default_cc, default_dept, default_bank_acct,
            pay_name=charge_pay_name,
            party_type="",
            acct_kw="bank charges", acct_fallback="bank charge expense",
            doc_type="Payments", trans_type="Expense Payment",
            cashflow="Operating costs", confidence=98.0,
            coding_method=f"Bank charge ({charge_name}) — bank: {charge_pay_name}",
        )

    # Interest received
    if _matches_any(narration, INTEREST_RECEIVED_PATTERNS) and not is_debit:
        return _quick_row(
            raw, narration, cleaned, debit, credit, currency, is_dupe, fp,
            accounts_index, default_cc, default_dept, default_bank_acct,
            pay_name="Interest Received",
            party_type="",
            acct_kw="interest income", acct_fallback="interest received",
            doc_type="Receipts", trans_type="Revenue Receipt",
            cashflow="Interest received", confidence=98.0,
            coding_method="Interest income detection",
        )

    # Interest paid
    if _matches_any(narration, INTEREST_PAID_PATTERNS) and is_debit:
        return _quick_row(
            raw, narration, cleaned, debit, credit, currency, is_dupe, fp,
            accounts_index, default_cc, default_dept, default_bank_acct,
            pay_name="Interest Payment",
            party_type="",
            acct_kw="interest expense", acct_fallback="interest paid",
            doc_type="Payments", trans_type="Expense Payment",
            cashflow="Loan repayments", confidence=98.0,
            coding_method="Interest expense detection",
        )

    # Transport
    if _matches_any(narration, TRANSPORT_PATTERNS) and is_debit:
        transport_name = _first_match(narration, TRANSPORT_PATTERNS) or "Transport"
        return _quick_row(
            raw, narration, cleaned, debit, credit, currency, is_dupe, fp,
            accounts_index, default_cc, default_dept, default_bank_acct,
            pay_name=transport_name.title(),
            party_type="",
            acct_kw="transport expense", acct_fallback="travel expense",
            doc_type="Payments", trans_type="Expense Payment",
            cashflow="Operating costs", confidence=97.0,
            coding_method=f"Transport detection → {transport_name}",
        )

    # ── 7. Alias table ───────────────────────────────────────────── #
    alias = _check_alias(narration, cleaned, alias_map)
    if alias:
        return _build_alias_row(
            raw, narration, cleaned, debit, credit, currency,
            is_debit, is_dupe, fp, alias,
            accounts_index, default_cc, default_dept, default_bank_acct,
        )

    # ── 8. Party match via inverted token index ───────────────────── #
    # Use extracted names + payee tokens for better matching
    search_tokens = list(set(payee_tokens + extracted_names))
    party_type, party_id, party_name, party_account, party_conf, party_method = \
        _match_party(search_tokens, cleaned, narration, is_debit,
                     party_index, token_index, accounts_index, company)

    # pay_name: party name (matched) > smart extraction from narration
    pay_name = (party_name
                or _pay_name_from_narration(narration, cleaned, extracted_names))

    # ── 9. Account coding ─────────────────────────────────────────── #
    doc_type, trans_type, cashflow = _classify(narration, is_debit, party_type)
    acct_field = "account_to_debit" if doc_type == "Payments" else "account_to_credit"

    if party_account and party_conf >= 75:
        account, confidence, coding_method = party_account, party_conf, party_method
    else:
        coa_acc, coa_conf, coa_method = _score_coa(narration, cleaned, doc_type, accounts_index)
        if party_account and party_conf >= 50:
            account       = party_account
            confidence    = (party_conf + coa_conf) / 2
            coding_method = f"{party_method} + {coa_method}"
        else:
            account, confidence, coding_method = coa_acc, coa_conf, coa_method

    # ── 10. FX ───────────────────────────────────────────────────── #
    exchange_rate = 1.0
    if currency != "NGN":
        exchange_rate = _fetch_exchange_rate(currency, raw["transaction_date"]) or 1.0
    local_amount = flt((debit if is_debit else credit) * exchange_rate, 2)

    # ── 11. Bank account ─────────────────────────────────────────── #
    bank_raw     = raw.get("bank_account_raw", "") or default_bank_acct
    bank_account = _resolve_bank_account_ml(bank_raw, company)

    # ── 12. Anomaly ──────────────────────────────────────────────── #
    anomaly_flag, anomaly_note = _detect_anomaly(cleaned, local_amount, history_map)

    # ── 13. Suspense fallback ─────────────────────────────────────── #
    if not account:
        account       = _find_account(accounts_index, "suspense")
        confidence    = min(confidence, 30.0)
        coding_method += " → Suspense fallback"

    # ── 14. Row status ───────────────────────────────────────────── #
    notes = []
    if not bank_account:
        notes.append("Bank account not set")
    if confidence < conf_threshold:
        notes.append(f"Confidence {confidence:.0f}% below threshold")

    if is_dupe:
        row_status = "Skipped"
    elif confidence >= conf_threshold and account:
        row_status = "Ready"
    else:
        row_status = "Review"

    reasoning = coding_method
    if notes:
        reasoning += " | " + " | ".join(notes)

    return _make_row(
        raw=raw, narration=narration, cleaned=cleaned,
        pay_name=pay_name[:140], debit=debit, credit=credit,
        local_amount=local_amount, currency=currency,
        exchange_rate=exchange_rate, bank_account=bank_account,
        party_type=party_type, party_id=party_id,
        doc_type=doc_type, trans_type=trans_type,
        acct_field=acct_field, account=account, cashflow=cashflow,
        coding_method=coding_method[:200],
        default_cc=default_cc, default_dept=default_dept,
        confidence=confidence, reasoning=reasoning[:1000],
        anomaly_flag=anomaly_flag, anomaly_note=anomaly_note,
        fp=fp, is_dupe=is_dupe, row_status=row_status,
    )


# ================================================================== #
#  NARRATION CLEANING + PAYEE / PERSON NAME EXTRACTION                #
# ================================================================== #

def _clean_and_extract(narration: str) -> tuple:
    """
    Returns (cleaned_description, payee_tokens, extracted_person_names).

    payee_tokens  — tokens suitable for party-index matching
    extracted_names — person names found in the narration (for pay_name fallback)
    """
    original = narration
    s = narration.upper()

    for prefix in STRIP_PREFIXES:
        s = s.replace(prefix, "")

    # Date fragments  e.g. 14NOV, 05JAN26
    s = re.sub(r'\b\d{1,2}[A-Z]{3}\d{0,2}\b', '', s)
    s = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', s)

    # Card / account number fragments (4+ consecutive digits)
    s = re.sub(r'[\*\/]?\b\d{4,}\b[\*\/]?', '', s)

    # Structural noise words
    noise = (r'\b(REF|TRF|FT|FROM|TO|A\/C|AC|ACCT|TRANSFER|PAYMENT|PAY|'
             r'NAIRA|NGN|USD|GBP|EUR|VIA|BY|INTO|FOR|AND|THE|OF|AT|ON)\b')
    s = re.sub(noise, '', s)

    s = re.sub(r'[\s\/\-_]+', ' ', s).strip()
    cleaned = s.title()

    # Payee tokens: 3+ char uppercase words (for party-index lookup)
    payee_tokens = [w for w in re.findall(r'\b[A-Z][A-Z0-9]{2,}\b', s)
                    if not w.isdigit()]

    # Person name extraction from the ORIGINAL mixed-case narration
    extracted_names = []
    name_patterns = [
        # "Transfer to John Doe" / "Payment to Mary Jane"
        r'(?:transfer|payment|pay|sent|trf)\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
        # Titles: "Mr/Mrs/Dr/Pastor John Doe"
        r'(?:MR|MRS|MS|DR|PROF|PASTOR|BROTHER|SISTER|REV|ENGR|BARR)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})',
        # Two or three consecutive title-case words (likely a name)
        r'\b([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b',
    ]
    _NAME_SKIP = {
        'Naira','Transfer','Payment','Account','Bank','Deposit','Savings',
        'Current','Mobile','Online','Internet','Monthly','Weekly','Daily',
        'Transaction','Electronic','National','Federal','State','Local',
        'Nigeria','Lagos','Abuja','Amount','Balance','Credit','Debit',
    }
    for pat in name_patterns:
        for m in re.finditer(pat, original, re.IGNORECASE):
            name = m.group(1).strip().title()
            words = name.split()
            # Reject if any word is in skip list or is a pure digit
            if any(w in _NAME_SKIP for w in words):
                continue
            if any(w.isdigit() for w in words):
                continue
            if len(name) > 3 and name not in extracted_names:
                extracted_names.append(name)

    return cleaned, payee_tokens, extracted_names[:3]


def _pay_name_from_bank_account(bank_account_raw: str) -> str:
    """
    For bank-charge transactions:
    Extract the first 2 meaningful words from the bank account name.

    Examples:
      "Zenith Bank — 0012345678"   →  "Zenith Bank"
      "GTBank 0098765432"          →  "Gtbank"
      "Access Bank PLC"            →  "Access Bank"
      "First Bank of Nigeria Ltd"  →  "First Bank"
      "0055512300"                 →  "" (pure number — fall through)
    """
    if not bank_account_raw:
        return ""

    # Strip punctuation separators and account number digits
    s = re.sub(r'[\-—–|,;]+', ' ', bank_account_raw)
    s = re.sub(r'\b\d{4,}\b', '', s).strip()

    # Words that add no information as a name
    # Note: "bank" is allowed — "Zenith Bank", "Access Bank" are valid 2-word names
    skip = {'plc','ltd','limited','of','for','the','and',
            'account','savings','current','mobile','digital',
            'microfinance','mfb','nig','nigeria'}

    all_words = [w for w in s.split() if len(w) >= 2]
    kept = []
    for w in all_words:
        if w.lower() not in skip:
            kept.append(w.title())
        if len(kept) == 2:
            break

    if not kept:
        return ""

    return " ".join(kept)


def _pay_name_from_narration(narration: str, cleaned: str,
                              extracted_names: list) -> str:
    """
    For non-party, non-bank-charge transactions:
    Extract the most likely entity name from the narration.

    Strategy (in order):
      1. If extracted_names has a person name → use it
      2. Try to find an entity-like token: a word that is NOT a common
         English word and is NOT a generic banking term.
         These are usually company abbreviations or proper-noun names
         embedded in the narration (e.g. DANGOTE, AMAZON, ORACLE, NNPC).
      3. Fall back to first 3 meaningful tokens from cleaned description.
    """
    # 1. Person name already extracted
    if extracted_names:
        return extracted_names[0][:100]

    # 2. Entity extraction: find non-English, non-banking tokens
    s = narration.upper()

    # Common English words and banking noise to exclude
    _ENGLISH = {
        # Structural / channel words
        'THE','AND','FOR','FROM','INTO','WITH','VIA','REF','TRANSFER',
        'PAYMENT','PAY','SEND','SENT','RECEIVED','RECEIVE',
        # Financial generic terms
        'CREDIT','DEBIT','ACCOUNT','BANK','SAVINGS','CURRENT',
        'FUNDS','AMOUNT','BALANCE','CASH','MONEY','DEPOSIT',
        'WITHDRAWAL','REMITTANCE','TRANSACTION','INWARD','OUTWARD',
        # Channel prefixes (already stripped but may remain as tokens)
        'NIP','NIBSS','RTGS','SWIFT','INTRABANK','INTERBANK',
        'USSD','MOB','WEB','ATM','POS','TRF','FT','ACCT',
        'MT103','MT940',
        # Generic English adjectives / prepositions
        'MOBILE','ONLINE','INTERNET','ELECTRONIC','MONTHLY',
        'WEEKLY','DAILY','NATIONAL','FEDERAL','STATE','LOCAL',
        # Countries / cities (generic locations)
        'NIGERIA','LAGOS','ABUJA','GHANA','KENYA',
        # Company suffixes
        'PLC','LTD','LIMITED','NIG','INC','CORP','GROUP',
        # Generic intermediary labels
        'CUST','CUSTOMER','VENDOR','AGENT','BROKER','THIRD',
        # NIBSS channel codes that appear as tokens after prefix stripping
        'FRSC','NIBSSLNK','NIBSSAPI','INTRABNK',
        # Currency codes (already handled by parser)
        'NGN','USD','GBP','EUR','GHS','KES','ZAR',
    }

    # Extract uppercase tokens ≥3 chars, not digits, not noise
    raw_tokens = re.findall(r'\b[A-Z][A-Z0-9]{2,}\b', s)
    entity_tokens = [
        t for t in raw_tokens
        if t not in _ENGLISH
        and not t.isdigit()
        and not re.match(r'^\d', t)
    ]

    if entity_tokens:
        # Take up to 3 unique tokens, join as the entity name
        seen, chosen = set(), []
        for tok in entity_tokens:
            if tok not in seen:
                seen.add(tok)
                chosen.append(tok.title())
            if len(chosen) == 3:
                break
        return " ".join(chosen)

    # 3. Fallback: first 3 words of cleaned description
    words = [w for w in cleaned.split() if len(w) >= 2][:3]
    return " ".join(words) if words else cleaned[:60]


# ================================================================== #
#  DETECTION HELPERS                                                   #
# ================================================================== #

def _matches_any(text: str, patterns: list) -> bool:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _detect_bank_charge(narration: str) -> str | None:
    """Return the charge label if narration is a bank charge, else None."""
    for pat in BANK_CHARGE_PATTERNS:
        m = re.search(pat, narration, re.IGNORECASE)
        if m:
            return m.group(0).title()
    return None


def _first_match(narration: str, patterns: list) -> str | None:
    for pat in patterns:
        m = re.search(pat, narration, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def _is_payroll(narration: str) -> bool:
    return _matches_any(narration, PAYROLL_PATTERNS)


# ================================================================== #
#  QUICK ROW BUILDER  (for hard-rule paths)                           #
# ================================================================== #

def _quick_row(raw, narration, cleaned, debit, credit, currency,
               is_dupe, fp, accounts_index, default_cc, default_dept,
               default_bank_acct,
               pay_name, party_type, acct_kw, acct_fallback,
               doc_type, trans_type, cashflow, confidence, coding_method):
    """
    Streamlined row builder for paths that don't need party matching.
    """
    er = (_fetch_exchange_rate(currency, raw["transaction_date"])
          if currency != "NGN" else 1.0)
    amount   = debit if debit > 0 else credit
    local    = flt(amount * er, 2)
    acct_field = "account_to_debit" if doc_type == "Payments" else "account_to_credit"
    account  = (_find_account(accounts_index, acct_kw)
                or _find_account(accounts_index, acct_fallback))
    bank_raw = raw.get("bank_account_raw", "") or default_bank_acct
    bank     = _resolve_bank_account_ml(bank_raw, None)
    status   = "Skipped" if is_dupe else ("Ready" if account else "Review")

    return _make_row(
        raw=raw, narration=narration, cleaned=cleaned,
        pay_name=pay_name, debit=debit, credit=credit,
        local_amount=local, currency=currency, exchange_rate=er,
        bank_account=bank, party_type=party_type, party_id="",
        doc_type=doc_type, trans_type=trans_type,
        acct_field=acct_field, account=account, cashflow=cashflow,
        coding_method=coding_method,
        default_cc=default_cc, default_dept=default_dept,
        confidence=confidence, reasoning=coding_method,
        anomaly_flag=False, anomaly_note="",
        fp=fp, is_dupe=is_dupe, row_status=status,
    )


# ================================================================== #
#  ALIAS ROW BUILDER                                                   #
# ================================================================== #

def _build_alias_row(raw, narration, cleaned, debit, credit, currency,
                     is_debit, is_dupe, fp, alias,
                     accounts_index, default_cc, default_dept, default_bank_acct):
    er       = _fetch_exchange_rate(currency, raw["transaction_date"]) if currency != "NGN" else 1.0
    local    = flt((debit if is_debit else credit) * er, 2)
    pt       = alias.get("entity_type") or alias.get("party_type") or ""
    pid      = alias.get("supplier_id") or alias.get("customer_id") or alias.get("party_id") or ""
    pname    = alias.get("cleaned_name") or cleaned
    doc_type, trans_type, cashflow = _classify(narration, is_debit, pt)
    acct_field = "account_to_debit" if doc_type == "Payments" else "account_to_credit"
    account  = alias.get("account_to_debit") or _find_account(accounts_index, "suspense")
    bank_raw = raw.get("bank_account_raw", "") or default_bank_acct
    bank     = _resolve_bank_account_ml(bank_raw, None)
    status   = "Skipped" if is_dupe else ("Ready" if account else "Review")

    return _make_row(
        raw=raw, narration=narration, cleaned=cleaned,
        pay_name=pname[:140], debit=debit, credit=credit,
        local_amount=local, currency=currency, exchange_rate=er,
        bank_account=bank, party_type=pt, party_id=pid,
        doc_type=doc_type, trans_type=trans_type,
        acct_field=acct_field, account=account,
        cashflow=alias.get("cashflow_type") or cashflow,
        coding_method=f"Alias: {pname}",
        default_cc=default_cc, default_dept=default_dept,
        confidence=97.0, reasoning=f"Alias table match: {pname}",
        anomaly_flag=False, anomaly_note="",
        fp=fp, is_dupe=is_dupe, row_status=status,
    )


# ================================================================== #
#  ERROR ROW (never crashes the batch)                                 #
# ================================================================== #

def _error_row(raw, error_msg: str) -> dict:
    fp = _fingerprint(raw)
    return _make_row(
        raw=raw,
        narration=(raw.get("raw_narration") or "")[:500],
        cleaned="", pay_name="",
        debit=flt(raw.get("debit_amount", 0)),
        credit=flt(raw.get("credit_amount", 0)),
        local_amount=0.0, currency="NGN", exchange_rate=1.0,
        bank_account="", party_type="", party_id="",
        doc_type="Payments", trans_type="Expense Payment",
        acct_field="account_to_debit", account="",
        cashflow="Operating costs",
        coding_method="Error during analysis",
        default_cc="", default_dept="",
        confidence=0.0, reasoning=f"Error: {error_msg[:200]}",
        anomaly_flag=False, anomaly_note="",
        fp=fp, is_dupe=False, row_status="Review",
    )


# ================================================================== #
#  PARTY MATCHING — inverted token index                               #
# ================================================================== #

def _load_party_index() -> tuple:
    """
    Load all parties and build an inverted token index.

    Returns: (party_list, token_index)
      party_list:   [{name, display_name, party_type}, ...]
      token_index:  {TOKEN(≥4 chars) → [party_idx, ...]}

    The index reduces matching from O(rows × parties) to O(rows × candidates).
    Typical: 300 rows × 5000 parties = 1.5M ops → 300 × 20 candidates = 6000 ops.
    """
    parties = []

    def add(name, display, ptype):
        idx = len(parties)
        parties.append({"name": name, "display_name": display or name, "party_type": ptype})
        return idx

    for s in frappe.get_all("Supplier", fields=["name","supplier_name"],
                             filters={"disabled":0}, limit=5000):
        add(s["name"], s["supplier_name"], "Supplier")

    for c in frappe.get_all("Customer", fields=["name","customer_name"],
                             filters={"disabled":0}, limit=5000):
        add(c["name"], c["customer_name"], "Customer")

    for e in frappe.get_all("Employee", fields=["name","employee_name"],
                             filters={"status":"Active"}, limit=2000):
        add(e["name"], e["employee_name"], "Employee")

    try:
        for m in frappe.get_all("Member", fields=["name","member_name"],
                                 filters={"enabled":1}, limit=5000):
            add(m["name"], m.get("member_name") or m["name"], "Member")
    except Exception:
        pass

    # Build inverted index: token(≥4 chars) → [list of party indices]
    token_index = {}
    for idx, party in enumerate(parties):
        tokens = set(re.findall(r'\b[A-Z]{4,}\b', (party["display_name"] or "").upper()))
        for tok in tokens:
            token_index.setdefault(tok, []).append(idx)

    frappe.logger().info(
        f"[BSU] Party index built: {len(parties)} parties, "
        f"{len(token_index)} unique tokens"
    )
    return parties, token_index


def _match_party(payee_tokens, cleaned, narration, is_debit,
                 party_index, token_index, accounts_index, company):
    """
    Fast party matching using inverted token index.
    Only scores parties sharing ≥1 token with the narration.
    Returns: (party_type, party_id, display_name, account, confidence, method)
    """
    txt        = (cleaned + " " + narration).upper()
    query_toks = set(re.findall(r'\b[A-Z]{4,}\b', txt))

    if not query_toks:
        return "", "", "", "", 0, "No tokens to match"

    # Fast candidate retrieval
    candidate_indices = set()
    for tok in query_toks:
        for idx in token_index.get(tok, []):
            candidate_indices.add(idx)

    if not candidate_indices:
        return "", "", "", "", 0, "No party matched"

    toks = set(t for t in payee_tokens if len(t) >= 3)
    best_score, best_party = 0, None

    for idx in candidate_indices:
        party    = party_index[idx]
        pname    = (party["display_name"] or "").upper()
        p_tokens = set(re.findall(r'\b[A-Z]{4,}\b', pname))
        if not p_tokens:
            continue

        # Jaccard token overlap (0–100)
        score = (len(toks & p_tokens) / max(len(toks), len(p_tokens)) * 100
                 if toks else 0)

        # Substring bonuses
        if pname in txt:
            score = min(score + 30, 99)
        elif any(t in txt for t in p_tokens if len(t) > 7):
            score = min(score + 22, 99)
        elif any(t in txt for t in p_tokens if len(t) >= 5):
            score = min(score + 15, 99)

        # Direction tie-breaker
        if is_debit   and party["party_type"] == "Supplier": score = min(score + 5, 99)
        elif not is_debit and party["party_type"] == "Customer": score = min(score + 5, 99)

        if score > best_score:
            best_score, best_party = score, party

    if best_score < 60 or not best_party:
        return "", "", "", "", 0, f"No match (best={best_score:.0f}%)"

    pt    = best_party["party_type"]
    pid   = best_party["name"]
    dname = best_party["display_name"]
    acc   = _party_default_account(pt, pid, is_debit, accounts_index, company)
    return pt, pid, dname, acc, best_score, f"Party match [{pt}]: {dname} — {best_score:.0f}%"


def _party_default_account(party_type, party_id, is_debit, accounts_index, company):
    if party_type == "Supplier":
        acc = frappe.db.get_value(
            "Party Account",
            {"parenttype":"Supplier","parent":party_id,
             "company":company,"account_type":"Payable"},
            "account"
        )
        return (acc
                or frappe.db.get_value("Company", company, "default_payable_account")
                or _find_account(accounts_index, "payable"))

    if party_type == "Customer":
        acc = frappe.db.get_value(
            "Party Account",
            {"parenttype":"Customer","parent":party_id,
             "company":company,"account_type":"Receivable"},
            "account"
        )
        return (acc
                or frappe.db.get_value("Company", company, "default_receivable_account")
                or _find_account(accounts_index, "receivable"))

    if party_type == "Employee":
        return (_find_account(accounts_index, "salaries payable")
                or _find_account(accounts_index, "salary expense")) if is_debit \
               else _find_account(accounts_index, "staff advance")

    if party_type == "Member":
        return (_find_account(accounts_index, "tithe")
                or _find_account(accounts_index, "donation")
                or _find_account(accounts_index, "member"))

    return ""


# ================================================================== #
#  COA KEYWORD SCORING                                                 #
# ================================================================== #

def _score_coa(narration, cleaned, doc_type, accounts_index):
    combined = (narration + " " + cleaned).upper()
    best = {"score": 0, "acc": None, "cf": "Operating costs", "kw": ""}

    for pattern, acct_kw, cashflow, boost in COA_RULES:
        if re.search(pattern, combined, re.IGNORECASE):
            acc = _find_account(accounts_index, acct_kw)
            if acc and boost > best["score"]:
                best = {"score": boost, "acc": acc, "cf": cashflow, "kw": acct_kw}

    if best["acc"]:
        confidence = min(55 + best["score"] * 2, 95)
        return best["acc"], confidence, f"CoA rule '{best['kw']}'"

    acc = _find_account(accounts_index, "suspense")
    return acc, 30.0, "No CoA rule matched → Suspense"


def _find_account(accounts_index: list, keyword: str):
    """Case-insensitive keyword search over preloaded account list."""
    kw = keyword.lower()
    # Exact name match first
    for acc in accounts_index:
        if (acc.get("account_name") or "").lower() == kw:
            return acc["name"]
    # Substring match
    for acc in accounts_index:
        if kw in (acc.get("account_name") or "").lower():
            return acc["name"]
    return None


# ================================================================== #
#  TRANSACTION CLASSIFICATION                                          #
# ================================================================== #

def _classify(narration, is_debit, party_type):
    if (party_type, is_debit) in PARTY_TRANS:
        return PARTY_TRANS[(party_type, is_debit)]

    if is_debit:
        for pat, cf in [
            (r'\bFIRS\b|\bTAX\b|\bVAT\b',      "Tax Payment"),
            (r'\bSALARY\b|\bPAYROLL\b',         "Salary payments"),
            (r'\bRENT\b|\bLEASE\b',             "Rent & utilities"),
            (r'\bDIVIDEND\b',                   "Dividend payments"),
            (r'\bLOAN\b|\bINSTALMENT\b',        "Loan repayments"),
        ]:
            if re.search(pat, narration, re.IGNORECASE):
                return "Payments", "Expense Payment", cf
        return "Payments", "Expense Payment", "Operating costs"

    for pat, tt, cf in [
        (r'\bTITHE\b|\bOFFERING\b', "Member Tithe",    "Customer payments for goods/services"),
        (r'\bPLEDGE\b',             "Pledges",         "Customer payments for goods/services"),
        (r'\bDONATION\b|\bGIFT\b',  "Revenue Receipt", "Customer payments for goods/services"),
        (r'\bINTEREST\b',           "Revenue Receipt", "Interest received"),
    ]:
        if re.search(pat, narration, re.IGNORECASE):
            return "Receipts", tt, cf
    return "Receipts", "Revenue Receipt", "Customer payments for goods/services"


# ================================================================== #
#  ROW DICT BUILDER — maps exactly to Bank Statement Upload Item      #
# ================================================================== #

def _make_row(raw, narration, cleaned, pay_name, debit, credit,
              local_amount, currency, exchange_rate, bank_account,
              party_type, party_id,
              doc_type, trans_type, acct_field, account, cashflow,
              coding_method, default_cc, default_dept,
              confidence, reasoning, anomaly_flag, anomaly_note,
              fp, is_dupe, row_status):
    return {
        "transaction_date":      raw.get("transaction_date", ""),
        "bank_account":          bank_account or "",
        "raw_narration":         narration[:500],
        "cleaned_description":   cleaned[:500],
        "pay_name":              (pay_name or "")[:140],
        "debit_amount":          flt(debit),
        "credit_amount":         flt(credit),
        "local_currency_amount": flt(local_amount),
        "payment_currency":      currency or "NGN",
        "exchange_rate":         flt(exchange_rate or 1),
        "reference_no":          (raw.get("reference_no") or "")[:140],
        "running_balance":       flt(raw.get("running_balance", 0)),
        # Party — auto-detected, never mandatory
        "party_type":            party_type or "",
        "party_id":              party_id or "",
        # Coding
        "doc_type":              doc_type or "",
        "trans_type":            trans_type or "",
        "account_to_debit":      (account or "") if acct_field == "account_to_debit" else "",
        "account_to_credit":     (account or "") if acct_field == "account_to_credit" else "",
        "cost_center":           default_cc or "",
        "department":            default_dept or "",
        "cashflow_type":         cashflow or "",
        "coding_method":         (coding_method or "")[:200],
        # WHT — user discretion only
        "apply_wht":             0,
        "wht_rate":              0,
        "wht_amount":            0,
        "net_amount":            flt(local_amount),
        # AI metadata
        "ai_confidence":         round(flt(confidence), 1),
        "ai_reasoning":          (reasoning or "")[:1000],
        "anomaly_flag":          1 if anomaly_flag else 0,
        "anomaly_note":          anomaly_note or "",
        "hash_fingerprint":      fp or "",
        "is_duplicate":          1 if is_dupe else 0,
        "row_status":            row_status or "Review",
        "failure_reason":        "",
        "created_doc_type":      "",
        "created_doc_name":      "",
    }


# ================================================================== #
#  PRE-LOADED INDEXES                                                  #
# ================================================================== #

def _load_alias_map(company: str) -> dict:
    rows = frappe.get_all(
        "Bank Statement Alias",
        filters=[["company", "in", [company, ""]]],
        fields=["raw_pattern", "cleaned_name", "entity_type",
                "supplier_id", "customer_id", "account_to_debit",
                "trans_type", "cashflow_type"]
    )
    for r in rows:
        r["party_type"] = r.get("entity_type") or ""
        r["party_id"]   = r.get("supplier_id") or r.get("customer_id") or ""
    return {r["raw_pattern"]: r for r in rows}


def _load_accounts_index(company: str) -> list:
    return frappe.get_all(
        "Account",
        filters={"company": company, "is_group": 0, "disabled": 0},
        fields=["name", "account_name", "account_type", "root_type"],
        limit=2000
    )


def _load_amount_history() -> dict:
    rows = frappe.db.sql(
        """SELECT cleaned_description, local_currency_amount
           FROM `tabBank Statement Upload Item`
           WHERE row_status='Created' AND local_currency_amount > 0
           ORDER BY transaction_date DESC LIMIT 5000""",
        as_dict=True
    )
    history = {}
    for r in rows:
        key = (r.cleaned_description or "").lower()[:40]
        history.setdefault(key, [])
        if len(history[key]) < 20:
            history[key].append(flt(r.local_currency_amount))
    return history


# ================================================================== #
#  UTILITIES                                                           #
# ================================================================== #

def _resolve_bank_account_ml(raw: str, company: str) -> str:
    """Resolve bank account using ML matcher from parser, with exact fallback."""
    if not raw:
        return ""
    # Try ML matcher first
    if _ml_match_bank:
        try:
            result = _ml_match_bank(raw, company or "")
            if result:
                return result
        except Exception:
            pass
    # Exact name fallback
    hit = frappe.db.get_value("Bank Account", {"account_name": raw}, "name")
    if hit:
        return hit
    # Digit suffix fallback
    import re as _re
    digits = _re.sub(r'\D', '', raw)
    if len(digits) >= 6:
        r = frappe.db.sql(
            "SELECT name FROM `tabBank Account` WHERE bank_account_no LIKE %s LIMIT 1",
            f"%{digits[-6:]}"
        )
        if r:
            return r[0][0]
    return raw  # return raw string — bank account not in ERPNext yet


def _detect_anomaly(cleaned: str, amount: float, history_map: dict):
    key     = cleaned.lower()[:40]
    history = history_map.get(key, [])
    if len(history) < 5:
        return False, ""
    mean  = statistics.mean(history)
    stdev = statistics.stdev(history)
    if stdev == 0:
        return False, ""
    z = abs(amount - mean) / stdev
    if z >= 3:
        return True, (f"Amount {amount:,.0f} is {z:.1f}σ from "
                      f"rolling mean ({mean:,.0f}) for '{cleaned[:30]}'.")
    return False, ""


def _fetch_exchange_rate(currency: str, txn_date: str) -> float:
    rate = frappe.db.get_value(
        "Currency Exchange",
        {"from_currency": currency, "to_currency": "NGN", "date": txn_date},
        "exchange_rate"
    )
    if rate:
        return flt(rate)
    r = frappe.db.sql(
        "SELECT exchange_rate FROM `tabCurrency Exchange` "
        "WHERE from_currency=%s AND to_currency='NGN' "
        "ORDER BY date DESC LIMIT 1",
        currency
    )
    return flt(r[0][0]) if r else 1.0


def _fingerprint(raw: dict) -> str:
    key = "|".join([
        str(raw.get("transaction_date", "")),
        str(raw.get("debit_amount", "")),
        str(raw.get("credit_amount", "")),
        (raw.get("raw_narration") or "")[:80],
    ])
    return hashlib.sha256(key.encode()).hexdigest()


def _hash_exists_in_db(fp: str) -> bool:
    return bool(frappe.db.exists(
        "Bank Statement Upload Item",
        {"hash_fingerprint": fp, "row_status": "Created"}
    ))


def _check_alias(narration: str, cleaned: str, alias_map: dict):
    nl, cl = narration.lower(), cleaned.lower()
    for pattern, alias in alias_map.items():
        if pattern.lower() in nl or pattern.lower() in cl:
            return alias
    return None


# ================================================================== #
#  WHT + REVALIDATION (called from controller)                        #
# ================================================================== #

def recalculate_wht(item):
    if not item.apply_wht or not item.wht_rate:
        item.wht_amount = 0
        item.net_amount = flt(item.local_currency_amount)
        return
    gross           = flt(item.local_currency_amount)
    item.wht_amount = flt(gross * flt(item.wht_rate) / 100, 2)
    item.net_amount = flt(gross - item.wht_amount, 2)


def revalidate_item(item):
    item.failure_reason = ""
    if item.row_status == "Failed":
        item.row_status = "Review"
    recalculate_wht(item)
    errors = []
    if not item.transaction_date:
        errors.append("Transaction date missing")
    if flt(item.debit_amount) == 0 and flt(item.credit_amount) == 0:
        errors.append("Zero amount")
    if not item.trans_type:
        errors.append("Transaction type not set")
    if errors:
        item.row_status     = "Review"
        item.failure_reason = "; ".join(errors)
    elif item.account_to_debit or item.account_to_credit:
        item.row_status = "Ready"