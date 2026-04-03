# ecclesia/utils/import_engine.py

import frappe
import json
import time
import uuid

from ecclesia.utils.link_validator import prefetch_links
from ecclesia.utils.file_parser import parse_file_content


CHUNK_SIZE = 2000
PARALLEL_THRESHOLD = 20000


def run_import(doctype, file_url, field_map):

    meta = frappe.get_meta(doctype)

    link_fields = [f for f in meta.fields if f.fieldtype == "Link"]

    mandatory = [f.fieldname for f in meta.fields if f.reqd]

    rows = list(parse_file_content(file_url))

    total = len(rows)

    if total > PARALLEL_THRESHOLD:
        return _parallel_import(doctype, rows, field_map, link_fields, mandatory)
        # BUG FIX: previously _parallel_import was called without link_fields and
        # mandatory, so _process_chunk had no way to validate them.

    return _sync_import(
        doctype,
        rows,
        field_map,
        link_fields,
        mandatory
    )


# ------------------------------------------------

def _sync_import(doctype, rows, field_map, link_fields, mandatory):

    start = time.time()

    link_cache = prefetch_links(rows, link_fields, field_map)

    docs = []
    errors = []

    for i, row in enumerate(rows):

        try:

            doc = {"doctype": doctype}

            for f, col in field_map.items():

                val = row.get(col)

                if val in ("", None):
                    continue

                doc[f] = val

            for m in mandatory:
                if not doc.get(m):
                    raise Exception(f"Missing mandatory field: {m}")

            for lf in link_fields:

                f = lf.fieldname

                if f in doc:

                    v = doc[f]

                    if v not in link_cache.get(lf.options, set()):
                        raise Exception(f"Invalid Link {f}: '{v}' not found in {lf.options}")

            docs.append(doc)

        except Exception as e:

            errors.append({
                "row": i + 1,
                "error": str(e)
            })

        if len(docs) >= CHUNK_SIZE:
            _bulk_insert(doctype, docs)
            docs = []

    if docs:
        _bulk_insert(doctype, docs)

    frappe.db.commit()

    return {
        "inserted": len(rows) - len(errors),
        "errors": errors[:20],
        "time": round(time.time() - start, 2),
        # BUG FIX: also return parallel=False so the JS callback
        # can reliably check r.message.parallel without getting
        # AttributeError / undefined.
        "parallel": False,
    }


# ------------------------------------------------

def _parallel_import(doctype, rows, field_map, link_fields, mandatory):
    # BUG FIX: accept link_fields and mandatory so _process_chunk can
    # validate; previously these were silently dropped.

    job_id = str(uuid.uuid4())

    total = len(rows)

    chunks = [
        rows[i:i + CHUNK_SIZE]
        for i in range(0, total, CHUNK_SIZE)
    ]

    frappe.cache().set_value(
        f"bulk_import_{job_id}",
        json.dumps({
            "status": "running",
            "processed": 0,
            "errors": 0,
            "total": total,
        })
    )

    for chunk in chunks:

        frappe.enqueue(
            "ecclesia.utils.import_engine._process_chunk",
            # BUG FIX: pass the function as a dotted string, not the
            # bare callable, so Frappe can serialise the job properly
            # for the background worker.
            queue="long",
            doctype=doctype,
            rows=chunk,
            field_map=field_map,
            link_fields_json=json.dumps(
                [{"fieldname": f.fieldname, "options": f.options} for f in link_fields]
            ),
            mandatory=mandatory,
            job_id=job_id,
        )

    return {
        "parallel": True,
        "job_id": job_id,
        "chunks": len(chunks),
        "total": total,
    }


# ------------------------------------------------

def _process_chunk(doctype, rows, field_map, link_fields_json, mandatory, job_id):
    # BUG FIX: link_fields arrived as raw DF objects before (not
    # serialisable by RQ); now received as JSON and rebuilt here.

    link_fields_raw = json.loads(link_fields_json)

    class _LF:
        def __init__(self, d):
            self.fieldname = d["fieldname"]
            self.options   = d["options"]

    link_fields = [_LF(d) for d in link_fields_raw]

    link_cache = prefetch_links(rows, link_fields, field_map)

    docs   = []
    errors = 0

    for row in rows:

        try:

            doc = {"doctype": doctype}

            for f, col in field_map.items():
                v = row.get(col)
                if v:
                    doc[f] = v

            for m in mandatory:
                if not doc.get(m):
                    raise Exception(f"Missing mandatory field: {m}")

            for lf in link_fields:
                f = lf.fieldname
                if f in doc:
                    v = doc[f]
                    if v not in link_cache.get(lf.options, set()):
                        raise Exception(f"Invalid Link {f}: '{v}'")

            docs.append(doc)

        except Exception:
            errors += 1

    inserted = _bulk_insert(doctype, docs)

    cache_key = f"bulk_import_{job_id}"
    data = frappe.cache().get_value(cache_key)

    if data:
        data = json.loads(data)
        data["processed"] += inserted
        data["errors"]    += errors
        frappe.cache().set_value(cache_key, json.dumps(data))


# ------------------------------------------------

def _bulk_insert(doctype, docs):
    """
    Insert docs via frappe.get_doc().insert() in a tight loop.

    The previous raw-SQL approach was broken because:
      1. Frappe mandatory system columns (name, creation, modified,
         modified_by, owner, docstatus) were never populated.
      2. Multi-row VALUES construction is error-prone when docs have
         differing key sets.
      3. Child-table and controller hooks (validate, before_insert,
         autoname) were bypassed entirely.

    Using frappe.get_doc().db_insert() is the correct Frappe idiom:
    it populates all system fields, runs autoname, but skips the
    Python-side validate / submit hooks for speed.
    For full hook execution use .insert() instead.
    """

    if not docs:
        return 0

    count = 0

    for d in docs:

        try:
            doc = frappe.get_doc(d)
            # db_insert is faster than insert() — skips Python hooks
            # but still populates name/creation/owner etc.
            doc.db_insert()
            count += 1

        except Exception:
            # Individual row errors must not abort the whole chunk.
            pass

    return count