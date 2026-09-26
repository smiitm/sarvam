"""Record -> structured JSON extraction.

Any extractor is just a callable `extract(path) -> dict` matching SCHEMA_KEYS.
The prototype uses `simulated_extract`, which "reads" a scan by looking up the
ground-truth JSON the sample generator wrote alongside it. To go live, write a
function that sends the file to an OCR/LLM API (e.g. Sarvam Document
Intelligence) and returns the same dict, then pass it to the pipeline instead.
"""
import json
from pathlib import Path

SCHEMA_KEYS = {"record_type", "patient", "visit_date", "doctor", "diagnosis",
               "medicines", "lab_values", "follow_up"}
MED_KEYS = {"name", "dose", "frequency", "duration_days"}
LAB_KEYS = {"test", "value", "unit", "ref_low", "ref_high"}


def validate(rec):
    """Enforce the strict schema; raises ValueError on any mismatch."""
    if set(rec) != SCHEMA_KEYS:
        raise ValueError(f"bad top-level keys: {set(rec) ^ SCHEMA_KEYS}")
    if not {"name", "age"} <= set(rec["patient"]):
        raise ValueError("patient needs name and age")
    for m in rec["medicines"]:
        if set(m) != MED_KEYS:
            raise ValueError(f"bad medicine keys: {m}")
    for l in rec["lab_values"]:
        if set(l) != LAB_KEYS:
            raise ValueError(f"bad lab keys: {l}")
    return rec


def simulated_extract(path):
    """Pretend-OCR: returns the structured JSON for an image/PDF path."""
    truth = Path(path).parent / "_extracted" / (Path(path).stem + ".json")
    return json.loads(truth.read_text())


def extract(path, extractor=simulated_extract):
    return validate(extractor(path))
