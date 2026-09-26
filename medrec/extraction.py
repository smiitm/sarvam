"""Record -> structured JSON extraction.

Any extractor is just a callable `extractor(path) -> dict` matching SCHEMA_KEYS.
- `sarvam_extract`: real pipeline. Sarvam Vision (Document Intelligence) OCRs the
  image/PDF to markdown, then Sarvam-105B structures that text into our schema.
- `simulated_extract`: offline fallback that returns the generator's ground-truth JSON.
"""
import io
import json
import os
import time
import urllib.request
import zipfile
from pathlib import Path

SCHEMA_KEYS = {"record_type", "patient", "visit_date", "doctor", "diagnosis",
               "medicines", "lab_values", "follow_up"}
MED_KEYS = {"name", "dose", "frequency", "duration_days"}
LAB_KEYS = {"test", "value", "unit", "ref_low", "ref_high"}

# JSON Schema handed to Sarvam-105B so its output matches the DB layout.
_str, _num, _int = {"type": "string"}, {"type": "number"}, {"type": "integer"}
JSON_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": sorted(SCHEMA_KEYS),
    "properties": {
        "record_type": {"type": "string", "enum": ["prescription", "lab_report", "discharge_summary"]},
        "patient": {"type": "object", "required": ["name", "age", "allergies"], "properties": {
            "name": _str, "age": _int, "allergies": {"type": "array", "items": _str}}},
        "visit_date": {"type": "string", "description": "YYYY-MM-DD"},
        "doctor": _str, "diagnosis": _str,
        "medicines": {"type": "array", "items": {"type": "object", "required": sorted(MED_KEYS), "properties": {
            "name": _str, "dose": _str, "frequency": _str, "duration_days": _int}}},
        "lab_values": {"type": "array", "items": {"type": "object", "required": sorted(LAB_KEYS), "properties": {
            "test": _str, "value": _num, "unit": _str, "ref_low": _num, "ref_high": _num}}},
        "follow_up": {"type": ["object", "null"], "required": ["instructions", "due_date"], "properties": {
            "instructions": _str, "due_date": {"type": ["string", "null"], "description": "YYYY-MM-DD"}}},
    },
}


def validate(rec):
    """Enforce the strict schema; raises ValueError on any mismatch."""
    if set(rec) != SCHEMA_KEYS:
        raise ValueError(f"bad top-level keys: {set(rec) ^ SCHEMA_KEYS}")
    if not {"name", "age"} <= set(rec["patient"]):
        raise ValueError("patient needs name and age")
    rec["patient"].setdefault("allergies", [])
    for m in rec["medicines"]:
        if set(m) != MED_KEYS:
            raise ValueError(f"bad medicine keys: {m}")
    for l in rec["lab_values"]:
        if set(l) != LAB_KEYS:
            raise ValueError(f"bad lab keys: {l}")
    fu = rec["follow_up"]
    if fu is not None and not fu.get("instructions"):
        rec["follow_up"] = None  # a follow-up with no instructions carries no information
    elif fu is not None:
        fu.setdefault("due_date", None)
    return rec


def simulated_extract(path):
    """Offline pretend-OCR: returns the structured JSON for an image/PDF path."""
    truth = Path(path).parent / "_extracted" / (Path(path).stem + ".json")
    return json.loads(truth.read_text())


def _client():
    from sarvamai import SarvamAI  # imported lazily so simulated mode needs no SDK
    return SarvamAI(api_subscription_key=os.environ["SARVAM_KEY"], timeout=300)


def sarvam_ocr(path):
    """Sarvam Vision: digitise an image/PDF and return its text as markdown."""
    client, path = _client(), Path(path)
    mime = "application/pdf" if path.suffix == ".pdf" else "image/jpeg"
    with open(path, "rb") as f:
        job = client.doc_ai.digitise(file=[(path.name, f, mime)], language="en-IN", output_format="md")
    deadline = time.time() + 180
    while True:
        if time.time() > deadline:
            raise TimeoutError(f"Sarvam digitise timed out for {path.name}")
        status = client.doc_ai.get_status(job_id=job.job_id).status.lower()
        if status in {"completed", "partially_completed"}:
            break
        if status in {"failed", "rejected"}:
            raise RuntimeError(f"Sarvam digitise {status} for {path.name}")
        time.sleep(3)
    url = client.doc_ai.get_download_url(job_id=job.job_id).url
    with zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url).read())) as z:  # output is a zip of .md pages
        return "\n".join(z.read(n).decode("utf-8") for n in sorted(z.namelist()) if n.endswith(".md"))


def sarvam_structure(text):
    """Sarvam-105B: turn OCR text into our strict JSON schema."""
    resp = _client().chat.completions(
        model="sarvam-105b",
        messages=[
            {"role": "system", "content": "You extract structured data from medical records. Use only facts "
             "in the text; use null/empty lists when absent. Dates as YYYY-MM-DD. duration_days is an integer."},
            {"role": "user", "content": text},
        ],
        temperature=0,
        reasoning_effort=None,
        response_format={"type": "json_schema", "json_schema": {"name": "medical_record", "schema": JSON_SCHEMA}},
    )
    return json.loads(resp.choices[0].message.content)


def sarvam_extract(path, retries=1):
    for attempt in range(retries + 1):
        try:
            return sarvam_structure(sarvam_ocr(path))
        except Exception:
            if attempt == retries:
                raise


def extract(path, extractor=simulated_extract):
    return validate(extractor(path))
