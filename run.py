"""End-to-end pipeline: generate synthetic scans -> extract -> store in SQLite -> HTML reports.

Usage: python run.py              # uses Sarvam APIs when SARVAM_KEY is set (env or .env)
       python run.py --simulate   # offline, no API calls
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from medrec import db, report, rules, samples
from medrec.extraction import extract, sarvam_extract, simulated_extract

ROOT = Path(__file__).parent
RECORDS_DIR, OUT_DIR = ROOT / "sample_records", ROOT / "output"


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def extract_one(scan, use_sarvam):
    """Extract via Sarvam; on any API error fall back to simulated so the demo always completes."""
    if use_sarvam:
        try:
            rec = extract(scan, sarvam_extract)
            print(f"  extracted {scan.name} via Sarvam", flush=True)
            return rec, "sarvam"
        except Exception as e:
            print(f"  ! Sarvam failed on {scan.name} ({e}); using simulated extraction")
    return extract(scan, simulated_extract), "simulated"


def main():
    load_env()
    use_sarvam = "--simulate" not in sys.argv and bool(os.environ.get("SARVAM_KEY"))
    print(f"Extraction: {'Sarvam Vision OCR + Sarvam-105B' if use_sarvam else 'simulated (offline)'}")
    OUT_DIR.mkdir(exist_ok=True)
    db_path = OUT_DIR / "records.db"
    db_path.unlink(missing_ok=True)  # fresh DB each run
    conn = db.connect(db_path)

    # 1-2. Extract all scans in parallel (each Sarvam OCR job takes ~1 min; 6 at a time).
    scans = samples.generate(RECORDS_DIR)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda s: extract_one(s, use_sarvam), scans))

    # 3. Store in order (existing patients are matched by name).
    for scan, (rec, source) in zip(scans, results):
        db.store_record(conn, rec, scan.name)
        print(f"ingested {scan.name} [{source}]")

    # Reports: one timeline + risk profile page per patient, plus an index.
    links = []
    for row in conn.execute("SELECT id, name FROM patients ORDER BY name"):
        p = db.patient_bundle(conn, row["id"])
        flags = rules.risk_flags(p)
        fname = row["name"].replace(" ", "_").lower() + ".html"
        (OUT_DIR / fname).write_text(report.render(p, flags), encoding="utf-8")
        links.append(f"<li><a href='{fname}'>{row['name']}</a> - {len(p['encounters'])} visits, "
                     f"{len(flags)} flags for doctor review</li>")
    (OUT_DIR / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>Patients</title>"
        "<body style='font-family:system-ui;max-width:700px;margin:24px auto'><h1>Patients</h1><ul>"
        + "".join(links) + "</ul></body>", encoding="utf-8")
    print(f"\n{len(links)} patient reports written. Open {OUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
