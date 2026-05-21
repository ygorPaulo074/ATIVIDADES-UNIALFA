"""
Extracts structured records from client-uploaded files.
Supports CSV, Excel, JSON, PDF, TXT and DOCX. Returns a list of dicts for indexing.
"""
import csv
import io
import json
from typing import Any


def extract(content: bytes, filename: str) -> list[dict[str, Any]]:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "csv":
        return _from_csv(content)
    if ext in ("xls", "xlsx"):
        return _from_excel(content)
    if ext == "json":
        return _from_json(content)
    if ext == "pdf":
        return _from_pdf(content)
    if ext == "txt":
        return _from_txt(content)
    if ext == "docx":
        return _from_docx(content)
    raise ValueError(f"Unsupported file type: .{ext}")


def _from_csv(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _from_excel(content: bytes) -> list[dict[str, Any]]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
    return [
        {headers[i]: cell for i, cell in enumerate(row)}
        for row in rows[1:]
        if any(cell is not None for cell in row)
    ]


def _from_json(content: bytes) -> list[dict[str, Any]]:
    data = json.loads(content.decode("utf-8"))
    if isinstance(data, list):
        return [item if isinstance(item, dict) else {"value": item} for item in data]
    if isinstance(data, dict):
        return [data]
    return [{"value": str(data)}]


def _from_txt(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    return [
        {"text": paragraph.strip()}
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]


def _from_docx(content: bytes) -> list[dict[str, Any]]:
    from docx import Document
    doc = Document(io.BytesIO(content))
    return [
        {"text": para.text.strip()}
        for para in doc.paragraphs
        if para.text.strip()
    ]


def _from_pdf(content: bytes) -> list[dict[str, Any]]:
    import pdfplumber
    records = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for paragraph in text.split("\n\n"):
                paragraph = paragraph.strip()
                if paragraph:
                    records.append({"text": paragraph})
    return records
