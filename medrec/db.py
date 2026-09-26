"""SQLite schema and storage helpers."""
import json
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, age INTEGER,
    allergies TEXT DEFAULT '[]'            -- JSON list, accumulated across records
);
CREATE TABLE IF NOT EXISTS encounters (
    id INTEGER PRIMARY KEY, patient_id INTEGER REFERENCES patients(id),
    visit_date TEXT, doctor TEXT, diagnosis TEXT, record_type TEXT, source_file TEXT
);
CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY, encounter_id INTEGER REFERENCES encounters(id),
    name TEXT, dose TEXT, frequency TEXT, duration_days INTEGER
);
CREATE TABLE IF NOT EXISTS lab_results (
    id INTEGER PRIMARY KEY, encounter_id INTEGER REFERENCES encounters(id),
    test TEXT, value REAL, unit TEXT, ref_low REAL, ref_high REAL
);
CREATE TABLE IF NOT EXISTS instructions (
    id INTEGER PRIMARY KEY, encounter_id INTEGER REFERENCES encounters(id),
    text TEXT, due_date TEXT
);
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert_patient(conn, p):
    """Return patient id; existing patients (matched by name) get age updated and allergies merged."""
    name = p["name"].strip()
    row = conn.execute("SELECT id, allergies FROM patients WHERE lower(name)=lower(?)", (name,)).fetchone()
    new_allergies = set(p.get("allergies", []))
    if row:
        merged = sorted(set(json.loads(row["allergies"])) | new_allergies)
        conn.execute("UPDATE patients SET age=?, allergies=? WHERE id=?",
                     (p.get("age"), json.dumps(merged), row["id"]))
        return row["id"]
    cur = conn.execute("INSERT INTO patients(name, age, allergies) VALUES (?,?,?)",
                       (name, p.get("age"), json.dumps(sorted(new_allergies))))
    return cur.lastrowid


def store_record(conn, rec, source_file):
    """Persist one extracted record (see extraction.SCHEMA_KEYS) into all tables."""
    pid = upsert_patient(conn, rec["patient"])
    eid = conn.execute(
        "INSERT INTO encounters(patient_id, visit_date, doctor, diagnosis, record_type, source_file) VALUES (?,?,?,?,?,?)",
        (pid, rec["visit_date"], rec["doctor"], rec["diagnosis"], rec["record_type"], source_file)).lastrowid
    for m in rec["medicines"]:
        conn.execute("INSERT INTO medications(encounter_id, name, dose, frequency, duration_days) VALUES (?,?,?,?,?)",
                     (eid, m["name"], m["dose"], m["frequency"], m["duration_days"]))
    for l in rec["lab_values"]:
        conn.execute("INSERT INTO lab_results(encounter_id, test, value, unit, ref_low, ref_high) VALUES (?,?,?,?,?,?)",
                     (eid, l["test"], l["value"], l["unit"], l["ref_low"], l["ref_high"]))
    fu = rec.get("follow_up")
    if fu:
        conn.execute("INSERT INTO instructions(encounter_id, text, due_date) VALUES (?,?,?)",
                     (eid, fu["instructions"], fu.get("due_date")))
    conn.commit()
    return pid


def patient_bundle(conn, pid):
    """Everything about one patient, encounters sorted chronologically."""
    patient = dict(conn.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone())
    patient["allergies"] = json.loads(patient["allergies"])
    encs = []
    for e in conn.execute("SELECT * FROM encounters WHERE patient_id=? ORDER BY visit_date", (pid,)):
        e = dict(e)
        for table, key in (("medications", "meds"), ("lab_results", "labs"), ("instructions", "instructions")):
            e[key] = [dict(r) for r in conn.execute(f"SELECT * FROM {table} WHERE encounter_id=?", (e["id"],))]
        encs.append(e)
    patient["encounters"] = encs
    return patient
