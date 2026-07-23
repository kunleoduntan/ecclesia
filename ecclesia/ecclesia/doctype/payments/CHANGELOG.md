# Payments — Consolidated Overhaul Changelog

## Module field corrected

`payments.json`'s `"module"` field was `"Production"` — you confirmed the
real module is `"Ecclesia"` (same name as the app). Fixed. This is
separate from the whitelisted method paths in `payments.py` /
`payments.js` / `payments_list.js`, which are **unchanged** — those were
already proven correct by your earlier `AttributeError` (Python resolved
`ecclesia.ecclesia.doctype.payments.payments` with no module segment in
it at all), so I didn't touch them again off a theoretical convention.
If `bench migrate` / doctype loading behaves differently after this field
change, that's a sign your physical folder layout doesn't match the
standard `app.app.module.doctype.doctype.doctype` convention — flag it
and I'll help sort out the actual layout rather than guess again.

## File count: 7+ files → 4 files

This DocType's server/client logic is now spread across exactly the
minimum Frappe allows:

| File | Role |
|---|---|
| `payments.json` | DocType definition |
| `payments.py` | ALL server logic — form controller, accounting entries, auto-coding, notifications, duplicate/balance checks, bulk import, dashboard analytics, doc_event hooks |
| `payments.js` | Form script |
| `payments_list.js` | List view script (import dialog, dashboard dialog, list settings) |

**Retire these — fully merged in, safe to delete:**
- `payment_utils.py` / `payment_utils__1_.py` (duplicate) — merged into `payments.py` in the previous round.
- `payments_import_handler.py` — merged into `payments.py` (see below).
- `payments_dashboard.py` — merged into `payments.py`, rewritten against the real schema (see below).
- `payments_import_list.js` / `payments_list.js` (these were identical duplicates of each other) — replaced by the single canonical `payments_list.js` in this delivery.

## Path convention — confirmed, unchanged this round

Every whitelisted call across all 4 files uses the confirmed-correct
`ecclesia.ecclesia.doctype.payments.payments.<method>` (no module-folder
segment) — proven correct by the `AttributeError` you hit last round.
`payments_import_list.js` had already been using this correctly; the
merge just moved its target methods from `payments_import_handler.py`
onto `payments.py`, same path prefix.

## payments_dashboard.py — rewritten, not just moved

The original file was badly out of sync with the real schema (and its own
header comment pointed at a different app, `general_biz_apps`, suggesting
it was copied in from elsewhere and never updated):

- Queried `payment_status IN ('Cleared', 'Bounced')` — those values don't
  exist; real options are `Draft/Pending/Approved/Processing/Completed/
  Failed/Cancelled/Rejected`. Rewritten to use real values.
- `get_payment_kpis` queried a `clearance_date` column that doesn't exist
  on this DocType at all — would have thrown a SQL error the first time
  it ran. Replaced with `DATEDIFF(modified, transaction_date)` as an
  explicitly-labeled *approximation* (see comment in code) — true
  clearance tracking would need a new dedicated date field.
- Bucketed `cashflow_type` into `'Operating'/'Investing'/'Financing'`
  literals that don't match any of the real 14 options. Replaced with a
  `CASHFLOW_IFRS_CATEGORY` mapping dict that derives the same 3-way IFRS
  summary correctly from the real field values.
- Summed `amount_paid` everywhere, which is only populated for
  local-currency payments — silently dropped every foreign-currency
  payment from every total. Now `COALESCE(local_currency_amount,
  amount_paid, 0)` throughout, consistent with the rest of the codebase.
- "Top payees" grouped on `payee_name` alone, which is blank for Supplier
  Payments (they use `supplier_name`/`payee_id`) — Supplier Payments,
  probably your highest-volume type, were invisible in that report. Fixed
  to `COALESCE(payee_name, supplier_name)`.
- `total_wht` was hardcoded to 0 with a comment claiming "WHT not in
  current system" — it is; fixed to `SUM(COALESCE(wht_amount, 0))`.
- Whitelisted entry point renamed `get_dashboard_data` → matches the
  richer `get_payment_dashboard_data` already in `payments.py` from the
  last round (single name now, no duplicate). **If any dashboard UI not
  shown to me calls `...payments_dashboard.get_dashboard_data`, update
  that call to `...payments.payments.get_payment_dashboard_data`.**
- Wired up in `payments_list.js` via a new "Payments Dashboard" menu item
  — previously these endpoints had no consuming UI in anything you'd
  shared, so they were dead code from the list view's perspective.

## payments_import_handler.py — merged, two bugs fixed

- **Hardcoded `'NGN'`** in both `validate_payments_import` and
  `import_payments` (`if payment_currency == "NGN"`) — same class of bug
  fixed in the DocType/JS last round. Now resolves the row's actual
  Company default currency via `_company_currency()` and compares
  against that. Template column labels changed from "Amount Paid (NGN)"
  to "Amount Paid (Local Currency)" to reflect this.
- **`frappe.log_error()` arguments were reversed** — every other call in
  the codebase (and the actual signature) is `log_error(message, title)`;
  this file alone called it backwards, which truncated full tracebacks
  into the 140-char title field and buried the useful row context in the
  short message field. Fixed.
- Dropped the pointless `frappe.flags.ignore_permissions = False` line
  (that's already the default — was a no-op).

## payments_list.js — consolidated + one functional fix

- Merged the two identical duplicate files into one.
- **"Process Payment" per-row button was a stub** — it only showed
  `frappe.msgprint('Processing payment: X')` with no actual effect. Now
  navigates to the document (`frappe.set_route('Form', 'Payments',
  doc.name)`) so the user can actually review/submit it, which is what
  the label promised.
- Added the "Payments Dashboard" menu item + dialog described above.

## Verification

All 4 files pass syntax checks (`py_compile` for Python, `new Function()`
parse for both JS files, `json.load` for the DocType JSON).

## Still on you

1. Delete the retired files listed at the top once you've confirmed
   nothing else references them (grep your app for
   `payments_import_handler` and `payments_dashboard` to be sure, since I
   can't see your full app tree).
2. Confirm no other page/report calls the old
   `payments_dashboard.get_dashboard_data` path directly.
3. If you want true bank-clearance-date tracking (as opposed to the
   `modified`-based approximation in `get_payment_kpis`), that needs a new
   field on the DocType — flag it and I'll add it properly rather than
   fake it further.

## Post-delivery fix: JE/PE not being created on submit

You reported payments submitting but not creating a Journal Entry or
Payment Entry. Root cause found in `on_submit()`:

**The bare `frappe.db.rollback()` in the accounting-entry exception
handler was rolling back the entire request transaction, not just the
failed entry-creation attempt.** Frappe runs a whole request (e.g. one
"Submit" click) as a single DB transaction that only commits at the very
end. Calling `frappe.db.rollback()` mid-`on_submit()` undoes everything
written so far in that transaction — including the submit's own
docstatus=1 write. The UI shows "submitted successfully" because that
message is built from the in-memory document object, not a fresh read
from the database, so the failure was invisible beyond an easy-to-miss
orange toast.

Fixed by using Frappe's savepoint API instead: `frappe.db.savepoint(name)`
before attempting entry creation, `frappe.db.rollback(save_point=name)` on
failure. This scopes the rollback to only the failed accounting-entry
attempt (and, separately, the failed amortization attempt, which had the
same latent issue even though you hadn't hit it yet) — leaving the
submit itself intact either way.

Also closed two related visibility/robustness gaps found while tracing
this:

- If accounting entries genuinely can't be created for a reason that
  doesn't raise an exception (returns an empty list) for a trans_type
  that should have produced entries, `on_submit` now shows an explicit
  orange warning instead of staying completely silent.
- If the "Create Accounting Entries" checkbox is off, `on_submit` now
  shows a blue informational message confirming that's why nothing was
  created — previously this path gave zero feedback, indistinguishable
  from a bug.
- `validate_accounts()` now fetches `remittance_bank_gl` and
  `bank_account_currency` server-side directly from the Bank Account,
  instead of relying solely on the client-side `fetch_from` mechanism.
  `fetch_from` only fires when a user changes the field on the form —
  documents created via the bulk importer, the API, or a script never
  got it populated, which would make `_validate_before_creation()` throw
  "Bank GL Account is required" during submit and silently block entry
  creation with no obvious cause.

## Behavior change: submission now REQUIRES accounting entries to exist

Per your explicit request — "any submitted Payments mean it has created
the necessary doc". Previous behavior (even after the savepoint fix)
still let a payment submit successfully even if its Journal Entry /
Payment Entry failed to create, just with a warning toast. That's gone.

**New behavior in `on_submit()`:** if `create_accounting_entries` is
checked, any failure creating the entries — missing Bank GL Account,
group account used for posting, misconfigured WHT account, anything —
now raises and is **not caught**. Frappe's own request handler rolls back
the entire transaction when an uncaught exception reaches it, which
undoes the submit itself (docstatus reverts to 0) since nothing commits
until the very end of the request. Net effect: a payment either submits
*with* its accounting entries, or it doesn't submit at all — there's no
in-between state anymore.

The one deliberate exception: if you uncheck "Create Accounting Entries"
yourself, that's an intentional opt-out, not a failure — those still
submit with just an informational blue notice, since there's nothing to
enforce in that case.

Amortization posting was deliberately left as best-effort/non-blocking —
it's a distinct concern (a whole future-dated schedule, not "was this
payment itself posted") and failing it shouldn't undo an otherwise-valid
payment that already has its real Journal/Payment Entry. Say the word if
you want that hardened the same way.

## New buttons on submitted Payments

- **"Create Journal Entry" / "Create Payment Entry"** (label adapts to
  `trans_type`) — mainly a recovery tool now: any payment submitted
  *before* this fix may have docstatus=1 with nothing actually posted.
  Safe to click even when entries already exist (just reports "already
  exist" and does nothing further).
- **"View Journal / Payment Entry"** — navigates straight to the created
  document. If a payment produced multiple entries (e.g. related-company
  payments post one JE per row), shows a quick picker instead of guessing
  which one you want.

Both live under an "Accounting" button group on submitted payments.

## Moved accounting-entry creation from on_submit to before_submit

Per your suggestion. Two improvements over the previous on_submit-based
approach:

1. **Cleaner failure semantics.** before_submit runs BEFORE docstatus is
   ever set to 1. If entry creation fails now, the throw happens before
   that write, rather than after it — no reliance on Frappe's transaction
   rollback to undo a docstatus write that technically already occurred.
   The submit simply never gets that far.

2. **Duplicate-creation guard.** before_submit now calls
   `controller.accounting_entries_exist()` first. If entries already exist
   for this reference_no (e.g. a first submit attempt failed partway, the
   issue was fixed, and Submit was clicked again — or the manual "Create
   Journal/Payment Entry" button was used before submitting for some
   reason), creation is skipped entirely with a blue notice instead of
   attempting to create a second set. The actual creation call also now
   passes `skip_duplicate_check=False` (was `True`) as a second layer of
   defense, so each individual JE/PE existence check still runs too.

`on_submit` is now much smaller — it only handles amortization posting
(still best-effort/non-blocking, unchanged), setting `payment_status` to
Completed, and the confirmation email. All three only run at all once
before_submit has already succeeded, so by the time you see any of them,
you know the accounting entries are real.
