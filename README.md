# Patient Medical Records Digitizer

This tool turns scanned prescriptions, lab reports and discharge summaries into one organized history per patient. For each patient it produces an HTML page with a visit timeline, current and past medications, lab trends and a risk profile.

It organizes records and does not diagnose anything. Every flag is labelled **"For doctor review"**. All patient data is synthetic.

## Quick start

```bash
pip install sarvamai pillow
python run.py              # uses Sarvam APIs if SARVAM_KEY is set in .env
python run.py --simulate   # offline, no API calls
```

Then open `output/index.html`.

## How it works

1. **Ingest**: `samples.py` creates records for 6 fake patients (17 in total) and saves them as JPG and PDF scans in `sample_records/`.
2. **Extract**:
   - Sarvam Vision (Document Intelligence) reads each scan and returns its text.
   - Sarvam-105B turns that text into a fixed JSON format: patient, visit date, doctor, diagnosis, medicines, lab values and follow-up.
   - If Sarvam fails on a record, that record falls back to simulated extraction.
3. **Store**: the data goes into SQLite at `output/records.db`, in tables for patients, encounters, medications, lab_results and instructions. If a patient is already on file, the new record joins their history and their allergies are merged.
4. **Flag**: a rules engine raises flags for:
   - long-term medication use that suggests a chronic condition
   - allergies on record
   - lab values that are out of range or getting worse
   - missed follow-ups
5. **Report**: one HTML page per patient, plus an index page.

## Project layout

| File | Purpose |
|---|---|
| `run.py` | Single-command pipeline |
| `medrec/extraction.py` | Extraction interface (Sarvam and simulated) and JSON format check |
| `medrec/db.py` | SQLite schema and storage |
| `medrec/rules.py` | Risk-flag rules |
| `medrec/report.py` | HTML report |
| `medrec/samples.py` | Synthetic data and scan rendering |

## Notes

- Patients are matched by name only (a prototype simplification).
- Current medications and missed follow-ups are worked out from today's date.
- Each Sarvam document job takes about a minute. The pipeline runs 6 at a time, with a 3-minute limit per job.
