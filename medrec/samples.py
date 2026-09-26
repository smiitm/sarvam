"""Generates synthetic (fake) patient records: placeholder scan files plus the
JSON the simulated OCR will 'extract' from them. No real patient data."""
import json
from pathlib import Path

DOCS = ["Dr. A. Rao", "Dr. S. Mehta", "Dr. K. Iyer"]


def med(name, dose, freq="Once daily", days=90):
    return {"name": name, "dose": dose, "frequency": freq, "duration_days": days}


def lab(test, value, unit, lo, hi):
    return {"test": test, "value": value, "unit": unit, "ref_low": lo, "ref_high": hi}


def rec(rtype, name, age, visit, doc, dx, meds=(), labs=(), fu=None, due=None, allergies=()):
    return {"record_type": rtype,
            "patient": {"name": name, "age": age, "allergies": list(allergies)},
            "visit_date": visit, "doctor": doc, "diagnosis": dx,
            "medicines": list(meds), "lab_values": list(labs),
            "follow_up": {"instructions": fu, "due_date": due} if fu else None}


def hba1c(v): return lab("HbA1c", v, "%", 4.0, 5.6)
def ldl(v): return lab("LDL cholesterol", v, "mg/dL", 0, 100)
def tsh(v): return lab("TSH", v, "mIU/L", 0.4, 4.0)
def hb(v): return lab("Hemoglobin", v, "g/dL", 12.0, 16.0)
def creat(v): return lab("Creatinine", v, "mg/dL", 0.6, 1.2)
def wbc(v): return lab("WBC", v, "x10^3/uL", 4.0, 11.0)


RECORDS = [
    # Ravi Kumar - diabetic, HbA1c worsening, missed last follow-up
    rec("prescription", "Ravi Kumar", 54, "2025-10-05", DOCS[0], "Type 2 diabetes mellitus",
        [med("Metformin", "500 mg", "Twice daily")], [hba1c(7.1)], "Review with HbA1c", "2026-01-05", ["Penicillin"]),
    rec("lab_report", "Ravi Kumar", 54, "2026-01-08", DOCS[0], "Diabetes follow-up",
        [med("Metformin", "500 mg", "Twice daily")], [hba1c(7.6), creat(1.1)], "Repeat labs in 3 months", "2026-04-08"),
    rec("prescription", "Ravi Kumar", 55, "2026-04-10", DOCS[0], "Diabetes, poorly controlled",
        [med("Metformin", "1000 mg", "Twice daily"), med("Glimepiride", "1 mg")], [hba1c(8.2)],
        "Return in 6 weeks", "2026-05-22"),
    # Priya Sharma - hypertension + dyslipidemia improving, sulfa allergy
    rec("prescription", "Priya Sharma", 61, "2025-11-12", DOCS[1], "Essential hypertension",
        [med("Amlodipine", "5 mg")], [ldl(142)], "BP check in 3 months", "2026-02-12", ["Sulfa drugs"]),
    rec("prescription", "Priya Sharma", 61, "2026-02-15", DOCS[1], "Hypertension, dyslipidemia",
        [med("Amlodipine", "5 mg"), med("Atorvastatin", "10 mg")], [ldl(128)], "Lipid profile in 3 months", "2026-05-15"),
    rec("lab_report", "Priya Sharma", 62, "2026-05-20", DOCS[1], "Routine monitoring",
        [med("Amlodipine", "5 mg"), med("Atorvastatin", "10 mg")], [ldl(96), creat(0.9)],
        "Continue meds; review in 4 months", "2026-09-20"),
    # Arjun Nair - acute pneumonia admission, then recovery
    rec("discharge_summary", "Arjun Nair", 34, "2026-03-02", DOCS[2], "Community-acquired pneumonia",
        [med("Amoxicillin-clavulanate", "625 mg", "Thrice daily", 7), med("Paracetamol", "650 mg", "As needed", 5)],
        [hb(13.5), wbc(14.2)], "Chest X-ray review in 2 weeks", "2026-03-16", ["Ibuprofen"]),
    rec("lab_report", "Arjun Nair", 34, "2026-03-18", DOCS[2], "Post-pneumonia review", [], [wbc(8.1)]),
    # Meena Pillai - hypothyroid on levothyroxine, hemoglobin falling
    rec("prescription", "Meena Pillai", 45, "2025-09-20", DOCS[0], "Hypothyroidism",
        [med("Levothyroxine", "50 mcg")], [tsh(6.8), hb(11.8)], "TSH in 3 months", "2025-12-20"),
    rec("lab_report", "Meena Pillai", 45, "2025-12-22", DOCS[0], "Thyroid follow-up",
        [med("Levothyroxine", "75 mcg"), med("Ferrous sulfate", "200 mg", "Once daily", 60)], [tsh(4.5), hb(11.2)],
        "Repeat TSH and CBC", "2026-03-22", ["Latex"]),
    rec("prescription", "Meena Pillai", 46, "2026-03-25", DOCS[0], "Hypothyroidism, iron-deficiency anemia",
        [med("Levothyroxine", "75 mcg"), med("Ferrous sulfate", "200 mg", "Twice daily", 90)], [tsh(3.1), hb(10.6)],
        "CBC in 3 months", "2026-06-25"),
    # Sanjay Gupta - asthma, repeated inhaler use, missed a follow-up
    rec("prescription", "Sanjay Gupta", 29, "2025-12-01", DOCS[1], "Bronchial asthma",
        [med("Salbutamol inhaler", "100 mcg", "As needed", 60)], [], "Review in 2 months", "2026-02-01", ["Aspirin"]),
    rec("prescription", "Sanjay Gupta", 29, "2026-02-03", DOCS[1], "Asthma, frequent symptoms",
        [med("Salbutamol inhaler", "100 mcg", "As needed", 90), med("Budesonide inhaler", "200 mcg", "Twice daily")],
        [], "Review in 3 months", "2026-05-03"),
    rec("prescription", "Sanjay Gupta", 30, "2026-07-10", DOCS[1], "Asthma exacerbation",
        [med("Salbutamol inhaler", "100 mcg", "As needed", 90), med("Budesonide inhaler", "200 mcg", "Twice daily"),
         med("Prednisolone", "20 mg", "Once daily", 5)], [], "Review in 1 month", "2026-08-10"),
    # Lakshmi Reddy - kidney function worsening, on BP meds
    rec("prescription", "Lakshmi Reddy", 68, "2025-10-18", DOCS[2], "Hypertension, CKD stage 2",
        [med("Telmisartan", "40 mg")], [creat(1.3)], "Renal function in 3 months", "2026-01-18"),
    rec("lab_report", "Lakshmi Reddy", 68, "2026-01-20", DOCS[2], "Renal monitoring",
        [med("Telmisartan", "40 mg")], [creat(1.5), hb(11.5)], "Nephrology review", "2026-04-20", ["Contrast dye"]),
    rec("discharge_summary", "Lakshmi Reddy", 69, "2026-06-05", DOCS[2], "Acute kidney injury on CKD, dehydration",
        [med("Telmisartan", "20 mg"), med("Oral rehydration salts", "1 sachet", "Thrice daily", 5)],
        [creat(1.9), hb(11.0)], "Renal function in 2 weeks", "2026-06-19", ["Penicillin"]),
]


def as_text(r):
    """Printed layout of a record, as it would appear on paper."""
    p = r["patient"]
    lines = [f"{r['doctor'].upper()} - CITY CARE CLINIC", r["record_type"].replace("_", " ").upper(), "",
             f"Patient: {p['name']}      Age: {p['age']}", f"Date of visit: {r['visit_date']}",
             f"Doctor: {r['doctor']}", f"Known allergies: {', '.join(p['allergies']) or 'None'}",
             f"Diagnosis: {r['diagnosis']}", ""]
    if r["medicines"]:
        lines.append("Rx:")
        lines += [f"  {i}. {m['name']} {m['dose']} - {m['frequency']} - {m['duration_days']} days"
                  for i, m in enumerate(r["medicines"], 1)]
    if r["lab_values"]:
        lines.append("Lab results:")
        lines += [f"  {l['test']}: {l['value']} {l['unit']}  (ref {l['ref_low']}-{l['ref_high']})"
                  for l in r["lab_values"]]
    if r["follow_up"]:
        lines += ["", f"Follow-up: {r['follow_up']['instructions']} by {r['follow_up']['due_date']}"]
    return "\n".join(lines)


def render(text, path):
    """Draw the record onto a white page and save as JPG or PDF (Pillow picks by extension)."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default(size=28)
    img = Image.new("RGB", (1240, 1000), "white")
    ImageDraw.Draw(img).multiline_text((60, 60), text, fill="black", font=font, spacing=14)
    img.save(path)


def generate(folder):
    """Write one scan (.jpg/.pdf) per record plus its ground-truth JSON (used by simulated mode)."""
    folder = Path(folder)
    (folder / "_extracted").mkdir(parents=True, exist_ok=True)
    paths = []
    for i, r in enumerate(RECORDS, 1):
        ext = ".jpg" if r["record_type"] == "prescription" else ".pdf"
        stem = f"{i:02d}_{r['patient']['name'].replace(' ', '_').lower()}_{r['record_type']}"
        scan = folder / (stem + ext)
        render(as_text(r), scan)
        (folder / "_extracted" / (stem + ".json")).write_text(json.dumps(r, indent=2))
        paths.append(scan)
    return paths
