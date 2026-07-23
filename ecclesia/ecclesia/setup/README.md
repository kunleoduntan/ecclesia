# Ecclesia DocType Self-Healing Installer

## What this is

14 of your DocTypes keep vanishing after `bench migrate`:

Fixed Asset Depreciation Schedule, Performance PIP, AML KYC Record,
Performance IDP, HR Calibration Session, CRM Account, CRM Contact,
HSE Inspection, Conflict of Interest Declaration, CRM Activity,
CRM Source, CRM Deal Stage, GL Audit Log, Audit Scope DocType.

All 14 fixture JSONs were validated before bundling (JSON parses, every
field in `fields` appears in `field_order` and vice versa, no duplicate
fieldnames, all submittable doctypes have `amended_from`, all correctly
scoped to `module: "Ecclesia"`) — no structural issues found in any of
them, so it's safe to use them as the recreation source.

## Why they likely keep disappearing

`bench migrate` reconciles DocTypes against files it finds on disk under
`apps/ecclesia/ecclesia/{module}/doctype/{name}/{name}.json`. Two things
commonly cause exactly this symptom:

1. **The files were never actually written to that location.** If these
   were created via Desk UI, Frappe normally auto-exports the .json to disk
   when `developer_mode = 1` — if that setting was off at creation time, or
   the module didn't resolve to a real folder, the DocType exists in the
   database only, with nothing on disk for migrate to sync from.
2. **Module registration mismatch.** All 14 are correctly set to
   `module: "Ecclesia"` in the JSON, but if that module folder isn't
   properly registered for the app (in `modules.txt`) at the path Frappe
   expects, migrate's disk walk won't find them there either.

**The permanent fix** is getting these files correctly placed under your
app's real module/doctype folder structure so ordinary `bench migrate`
sync handles them like any other standard DocType, with no custom code
needed. This installer is the safety net that works regardless — it
never touches the filesystem sync mechanism, it just checks the database
directly and recreates anything missing from a bundled definition.

## Files in this bundle

- `ensure_doctypes.py` — the core logic. Drop at
  `ecclesia/ecclesia/setup/ensure_doctypes.py`
- `fixtures/*.json` — the 14 validated DocType definitions, used as the
  recreation source. Drop the whole `fixtures/` folder alongside
  `ensure_doctypes.py`, i.e. at `ecclesia/ecclesia/setup/fixtures/`
- `commands.py` — optional, for a nicer `bench ensure-doctypes` command.
  Drop at `ecclesia/ecclesia/setup/commands.py`

(If `ecclesia/ecclesia/setup/` doesn't exist yet as a Python package,
add an empty `__init__.py` in that folder too.)

## Wiring it up — pick what you want

### Option A: automatic, every `bench migrate`
Add to `hooks.py`:
```python
after_migrate = ["ecclesia.ecclesia.setup.ensure_doctypes.ensure_doctypes_exist"]
```
If `after_migrate` already exists as a list in your hooks.py, append this
string to it rather than overwriting the whole line.

### Option B: on demand, zero extra wiring
```bash
bench --site your-site.local execute ecclesia.ecclesia.setup.ensure_doctypes.ensure_doctypes_exist
```
This works immediately once `ensure_doctypes.py` + `fixtures/` are in
place — no hooks.py changes needed at all.

### Option C: on demand, nicer command
Add to `hooks.py`:
```python
commands = ["ecclesia.ecclesia.setup.commands.commands"]
```
Then:
```bash
bench --site your-site.local ensure-doctypes
bench --site your-site.local ensure-doctypes --force-update
```

## What `force_update` does (and doesn't do)

- Default (no flag): only **creates** DocTypes that are completely
  missing. Never touches ones that already exist in the database —
  always safe to run, including automatically after every migrate.
- `force_update=True`: for DocTypes that already exist, also re-applies
  the bundled `fields`/`field_order`/layout definition from the JSON, in
  case the live DocType has drifted from the fixture (e.g. you edited it
  in the UI and want to reset it back to the known-good definition).
  **This never touches actual records/data** in the doctype's own table
  — only its schema (the DocType's own field list), exactly like editing
  the DocType in Desk would.

## After running

Check the output — it prints a one-line summary (created/updated/
skipped/failed counts) plus the name and error for anything that failed.
Failures are also logged to the normal Frappe Error Log
(`frappe.log_error`), so `bench --site your-site.local console` →
`frappe.get_all("Error Log", filters={"method": ["like", "%ensure_doctypes%"]})`
will show you the full traceback for anything that didn't recreate cleanly.

## One thing worth doing separately

Since I can't see your actual `apps/ecclesia` folder structure, I can't
confirm whether these 14 doctypes' .json files genuinely aren't on disk,
or are on disk in the wrong place, or something else entirely is deleting
them. If you can run:
```bash
find apps/ecclesia -iname "*.json" | grep -iE "aml_kyc|performance_pip|crm_account|hse_inspection|gl_audit_log"
```
and share what comes back (or nothing, if truly absent), I can tell you
definitively which of the two causes above it is, and give you the exact
`bench migrate`-native fix instead of relying on this safety net.
