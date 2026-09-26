"""End-to-end pipeline: generate synthetic scans -> extract -> store in SQLite -> HTML reports.

Usage: python run.py
"""
from pathlib import Path

from medrec import db, report, rules, samples
from medrec.extraction import extract

ROOT = Path(__file__).parent
RECORDS_DIR, OUT_DIR = ROOT / "sample_records", ROOT / "output"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    db_path = OUT_DIR / "records.db"
    db_path.unlink(missing_ok=True)  # fresh DB each run
    conn = db.connect(db_path)

    # 1-3. Ingest each scan: extract structured JSON, then store (existing patients are matched by name).
    for scan in samples.generate(RECORDS_DIR):
        db.store_record(conn, extract(scan), scan.name)
        print(f"ingested {scan.name}")

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
