# ecclesia/ecclesia/doctype/bank_statement_upload/bank_statement_upload.py

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, flt, cint
import json


class BankStatementUpload(Document):

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def validate(self):
        self._set_imported_by()
        self._validate_column_mapping()

    def on_submit(self):
        pass

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _set_imported_by(self):
        if not self.imported_by:
            self.imported_by = frappe.session.user

    def _validate_column_mapping(self):
        if not self.date_column:
            frappe.throw("Date Column is required in Column Mapping.")
        if not self.narration_column:
            frappe.throw("Narration / Description Column is required.")
        if not self.get("bank_account_column") and not self.get("default_bank_account"):
            frappe.msgprint(
                "No Bank Account column or default bank account set. "
                "Bank account will be blank — set before creating documents.",
                indicator="orange", alert=True
            )

    def _update_summary(self):
        items = self.import_items or []
        self.total_rows   = len(items)
        self.rows_ready   = sum(1 for i in items if i.row_status == "Ready")
        self.rows_review  = sum(1 for i in items if i.row_status == "Review")
        self.rows_failed  = sum(1 for i in items if i.row_status == "Failed")
        self.rows_skipped = sum(1 for i in items if i.row_status == "Skipped")
        self.rows_created = sum(1 for i in items if i.row_status == "Created")

    def _append_log(self, message: str):
        ts = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
        existing = self.import_log or ""
        self.import_log = f"{existing}\n[{ts}] {message}".strip()

    def _safe_save(self, staged_rows=None, status=None, log=None):
        """
        Save the document without losing in-memory child rows
        and without a TimestampMismatchError.

        Pattern:
          1. Capture status/log/rows we want to write
          2. reload() — syncs modified timestamp from DB (wipes in-memory state)
          3. Re-apply captured state
          4. save(ignore_version=True) — writes cleanly
        """
        # Capture state before reload wipes it
        save_status = status or self.import_status
        save_log    = log    or self.import_log
        save_rows   = staged_rows  # None = use current self.import_items

        self.reload()  # syncs timestamp — wipes everything else

        # Re-apply all state
        self.import_status = save_status
        self.import_log    = save_log

        if save_rows is not None:
            self.import_items = []
            for row_dict in save_rows:
                self.append("import_items", row_dict)
        # If save_rows is None: self.import_items was reloaded from DB
        # (correct for _save_with_current_items path)

        self._update_summary()
        self.save(ignore_version=True)

    # ------------------------------------------------------------------ #
    #  parse_and_stage                                                     #
    # ------------------------------------------------------------------ #

    def parse_and_stage(self):
        from ecclesia.ecclesia.doctype.bank_statement_upload.parser import parse_file

        # Signal parsing started
        frappe.db.set_value(
            "Bank Statement Upload", self.name,
            {"import_status": "Parsing", "import_log": ""},
            update_modified=False
        )
        frappe.db.commit()

        try:
            # ── Step 1: Parse file (fast — just reads bytes) ────────────── #
            raw_rows = parse_file(self)
            msg = f"Parsed {len(raw_rows)} rows. Starting AI analysis..."
            frappe.db.set_value(
                "Bank Statement Upload", self.name, "import_log", msg,
                update_modified=False
            )
            frappe.db.commit()

            # ── Step 2: Route based on row count ────────────────────────── #
            # For ≤150 rows: run inline (fast enough for gunicorn timeout)
            # For  >150 rows: enqueue as background job (avoids timeout)
            INLINE_LIMIT = 150

            if len(raw_rows) <= INLINE_LIMIT:
                return self._run_analysis_inline(raw_rows)
            else:
                return self._enqueue_analysis(raw_rows)

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Bank Statement Upload — parse error")
            frappe.db.set_value(
                "Bank Statement Upload", self.name,
                {"import_status": "Completed with Errors",
                 "import_log": f"ERROR: {str(e)}"},
                update_modified=False
            )
            frappe.db.commit()
            frappe.throw(str(e))

    def _run_analysis_inline(self, raw_rows: list) -> dict:
        """Run AI analysis inline (≤150 rows — safe for gunicorn timeout)."""
        from ecclesia.ecclesia.doctype.bank_statement_upload.ai_coder import analyse_rows

        staged = analyse_rows(raw_rows, self)
        self.import_log = (
            f"Parsed {len(raw_rows)} rows. "
            f"Ready: {sum(1 for r in staged if r.get('row_status')=='Ready')}, "
            f"Review: {sum(1 for r in staged if r.get('row_status')=='Review')}, "
            f"Skipped: {sum(1 for r in staged if r.get('row_status')=='Skipped')}."
        )
        self._safe_save(staged_rows=staged, status="Staging", log=self.import_log)
        self.reload()
        return {
            "total":  self.total_rows,
            "ready":  self.rows_ready,
            "review": self.rows_review,
            "failed": self.rows_failed,
            "queued": False,
        }

    def _enqueue_analysis(self, raw_rows: list) -> dict:
        """Enqueue AI analysis as background job (>150 rows)."""
        import json as _json

        # Serialise raw_rows to DB so the background job can read them
        frappe.db.set_value(
            "Bank Statement Upload", self.name,
            {"import_status": "Parsing",
             "import_log": f"Queued analysis of {len(raw_rows)} rows..."},
            update_modified=False
        )
        frappe.db.commit()

        frappe.enqueue(
            "ecclesia.ecclesia.doctype.bank_statement_upload.bank_statement_upload"
            ".run_analysis_job",
            import_name=self.name,
            raw_rows=raw_rows,
            queue="long",
            timeout=600,
            job_name=f"bsu_analyse_{self.name}",
        )
        return {
            "total":  len(raw_rows),
            "ready":  0,
            "review": 0,
            "failed": 0,
            "queued": True,
            "message": (f"{len(raw_rows)} rows queued for background analysis. "
                        "Refresh the form in a moment to see results."),
        }

    # ------------------------------------------------------------------ #
    #  create_transactions                                                 #
    # ------------------------------------------------------------------ #

    def create_transactions(self):
        mode = self.creation_mode or "Batch"
        ready_count = sum(
            1 for i in self.import_items
            if i.row_status in ("Ready", "Review")
        )
        if ready_count == 0:
            frappe.throw("No rows in Ready or Review status. Nothing to create.")

        if mode == "Immediate" or ready_count <= 200:
            return self._create_immediate()
        return self._enqueue_batch()

    def _create_immediate(self):
        from ecclesia.ecclesia.doctype.bank_statement_upload.creator import create_document

        frappe.db.set_value(
            "Bank Statement Upload", self.name,
            "import_status", "Creating", update_modified=False
        )
        frappe.db.commit()

        created = failed = 0
        for item in self.import_items:
            if item.row_status not in ("Ready", "Review"):
                continue
            result = create_document(item, self)
            if result["success"]:
                item.row_status       = "Created"
                item.created_doc_type = result["doctype"]
                item.created_doc_name = result["name"]
                created += 1
            else:
                item.row_status     = "Failed"
                item.failure_reason = result["error"]
                failed += 1

        self.import_status = "Completed" if failed == 0 else "Completed with Errors"
        self._append_log(f"Done. Created: {created}, Failed: {failed}.")
        # _safe_save without staged_rows: just reload timestamp, keep existing child rows
        # We can't use _safe_save(staged_rows=...) here because item objects are already
        # modified in-place — convert them to dicts first
        self._save_with_current_items()
        return {"created": created, "failed": failed}

    def _save_with_current_items(self):
        """Save the document preserving the current in-memory child rows."""
        # Capture current item state as plain dicts
        current_items = []
        for item in (self.import_items or []):
            d = item.as_dict()
            d.pop("name", None)          # let Frappe re-assign row IDs
            d.pop("owner", None)
            d.pop("creation", None)
            d.pop("modified", None)
            d.pop("modified_by", None)
            d.pop("docstatus", None)
            current_items.append(d)

        self.reload()                    # sync timestamp
        self.import_status = self.import_status  # re-apply (reload cleared it)
        self.import_items = []
        for d in current_items:
            self.append("import_items", d)
        self._update_summary()
        self.save(ignore_version=True)

    def _enqueue_batch(self):
        frappe.enqueue(
            "ecclesia.ecclesia.doctype.bank_statement_upload.creator.run_batch",
            import_name=self.name,
            batch_size=cint(self.batch_size) or 50,
            queue="long",
            timeout=3600,
            job_name=f"bsu_create_{self.name}"
        )
        frappe.db.set_value(
            "Bank Statement Upload", self.name,
            "import_status", "Creating", update_modified=False
        )
        frappe.db.commit()
        return {"queued": True, "job": f"bsu_create_{self.name}"}

    # ------------------------------------------------------------------ #
    #  bulk_recode                                                         #
    # ------------------------------------------------------------------ #

    def bulk_recode(self, row_names: list, recode_values: dict):
        from ecclesia.ecclesia.doctype.bank_statement_upload.ai_coder import revalidate_item

        recode_values = json.loads(recode_values) if isinstance(recode_values, str) else recode_values
        row_names     = json.loads(row_names)      if isinstance(row_names, str)     else row_names

        updated = 0
        for item in self.import_items:
            if item.name not in row_names:
                continue
            for field, value in recode_values.items():
                if value and value != "— keep existing —":
                    item.set(field, value)
            revalidate_item(item)
            updated += 1

        self._append_log(f"Bulk recode applied to {updated} rows.")
        self._save_with_current_items()
        return {"updated": updated}

    # ------------------------------------------------------------------ #
    #  export_staged                                                       #
    # ------------------------------------------------------------------ #

    def export_staged(self):
        """Export all staged rows to Excel for download and review."""
        from ecclesia.ecclesia.doctype.bank_statement_upload.exporter import export_staged_rows

        if not self.import_items:
            frappe.throw("No staged rows to export. Run Analyse File first.")

        file_url = export_staged_rows(self.import_items, self.name)
        return {"file_url": file_url}

    # ------------------------------------------------------------------ #
    #  export_failed_rows                                                  #
    # ------------------------------------------------------------------ #

    def export_failed_rows(self):
        from ecclesia.ecclesia.doctype.bank_statement_upload.exporter import export_failed

        failed_items = [i for i in self.import_items if i.row_status == "Failed"]
        if not failed_items:
            frappe.throw("No failed rows to export.")

        file_url = export_failed(failed_items, self.name)
        return {"file_url": file_url}

    # ------------------------------------------------------------------ #
    #  get_progress                                                        #
    # ------------------------------------------------------------------ #

    def get_progress(self):
        self.reload()
        self._update_summary()
        return {
            "status":   self.import_status,
            "total":    self.total_rows,
            "created":  self.rows_created,
            "failed":   self.rows_failed,
            "review":   self.rows_review,
            "skipped":  self.rows_skipped,
            "log_tail": (self.import_log or "")[-800:],
        }


# ================================================================== #
#  MODULE-LEVEL WHITELIST WRAPPERS                                     #
# ================================================================== #

@frappe.whitelist()
def parse_and_stage(doc_name: str = None, **kwargs):
    name = doc_name or frappe.form_dict.get("docname") or frappe.form_dict.get("name")
    doc  = frappe.get_doc("Bank Statement Upload", name)
    return doc.parse_and_stage()


@frappe.whitelist()
def create_transactions(doc_name: str = None, **kwargs):
    name = doc_name or frappe.form_dict.get("docname") or frappe.form_dict.get("name")
    doc  = frappe.get_doc("Bank Statement Upload", name)
    return doc.create_transactions()


@frappe.whitelist()
def bulk_recode(doc_name: str = None, row_names=None, recode_values=None, **kwargs):
    name          = doc_name or frappe.form_dict.get("docname") or frappe.form_dict.get("name")
    row_names     = json.loads(row_names)     if isinstance(row_names, str)     else (row_names or [])
    recode_values = json.loads(recode_values) if isinstance(recode_values, str) else (recode_values or {})
    doc = frappe.get_doc("Bank Statement Upload", name)
    return doc.bulk_recode(row_names, recode_values)


@frappe.whitelist()
def export_staged(doc_name: str = None, **kwargs):
    name = doc_name or frappe.form_dict.get("docname") or frappe.form_dict.get("name")
    doc  = frappe.get_doc("Bank Statement Upload", name)
    return doc.export_staged()


@frappe.whitelist()
def export_failed_rows(doc_name: str = None, **kwargs):
    name = doc_name or frappe.form_dict.get("docname") or frappe.form_dict.get("name")
    doc  = frappe.get_doc("Bank Statement Upload", name)
    return doc.export_failed_rows()


@frappe.whitelist()
def get_progress(doc_name: str = None, **kwargs):
    name = doc_name or frappe.form_dict.get("docname") or frappe.form_dict.get("name")
    doc  = frappe.get_doc("Bank Statement Upload", name)
    return doc.get_progress()


# ================================================================== #
#  BACKGROUND JOB — runs for large uploads (>150 rows)                #
# ================================================================== #

@frappe.whitelist()
def run_analysis_job(import_name: str, raw_rows: list, **kwargs):
    """
    Frappe background job: runs AI analysis for large uploads.
    Called by frappe.enqueue — not directly by the user.
    """
    from ecclesia.ecclesia.doctype.bank_statement_upload.ai_coder import analyse_rows

    doc = frappe.get_doc("Bank Statement Upload", import_name)

    try:
        staged = analyse_rows(raw_rows, doc)

        ready  = sum(1 for r in staged if r.get("row_status") == "Ready")
        review = sum(1 for r in staged if r.get("row_status") == "Review")
        skipped = sum(1 for r in staged if r.get("row_status") == "Skipped")

        log = (f"Background analysis complete. "
               f"Total: {len(staged)}, Ready: {ready}, "
               f"Review: {review}, Skipped: {skipped}.")

        doc._safe_save(staged_rows=staged, status="Staging", log=log)

        # Notify user via Frappe realtime
        frappe.publish_realtime(
            event="bsu_analysis_complete",
            message={"import_name": import_name,
                     "total": len(staged), "ready": ready,
                     "review": review, "status": "Staging"},
            user=doc.owner
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "BSU background analysis failed")
        frappe.db.set_value(
            "Bank Statement Upload", import_name,
            {"import_status": "Completed with Errors",
             "import_log": f"Background analysis failed: {str(e)}"},
            update_modified=False
        )
        frappe.db.commit()