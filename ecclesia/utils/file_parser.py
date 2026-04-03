# ecclesia/utils/file_parser.py

import csv
import io
import frappe

try:
    import openpyxl
except Exception:
    openpyxl = None


def parse_file_content(file_url):

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    content = file_doc.get_content()

    if file_url.lower().endswith(".csv"):
        return stream_csv(content)

    if file_url.lower().endswith(".xlsx"):
        return parse_excel(content)

    raise Exception("Unsupported file format")


def stream_csv(content):

    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    for row in reader:
        yield row


def parse_excel(content):

    if not openpyxl:
        frappe.throw("openpyxl not installed")

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    ws = wb.active

    headers = [c.value for c in next(ws.rows)]

    for row in ws.iter_rows(values_only=True):

        values = dict(zip(headers, row))
        yield values