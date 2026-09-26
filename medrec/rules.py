"""Rule-based risk flags. Every flag is for doctor review only - not a diagnosis."""
from datetime import date, timedelta

REVIEW = "For doctor review"
# Long-term use of these medicines commonly indicates a chronic condition.
CHRONIC_MEDS = {
    "metformin": "Type 2 diabetes", "glimepiride": "Type 2 diabetes",
    "amlodipine": "Hypertension", "telmisartan": "Hypertension",
    "atorvastatin": "Dyslipidemia", "levothyroxine": "Hypothyroidism",
    "salbutamol inhaler": "Asthma / COPD",
}


def d(s):
    return date.fromisoformat(s)


def risk_flags(p, today=None):
    today = today or date.today()
    encs = p["encounters"]
    flags = []

    # 1. Chronic-condition indicators: same medicine prescribed in 3+ visits spanning 90+ days.
    seen = {}
    for e in encs:
        for m in e["meds"]:
            seen.setdefault(m["name"].lower(), []).append(d(e["visit_date"]))
    for med, dates in seen.items():
        span = (max(dates) - min(dates)).days
        if len(dates) >= 3 and span >= 90:
            cond = CHRONIC_MEDS.get(med, "a long-term condition")
            flags.append(("Chronic condition indicator",
                          f"{med.title()} prescribed at {len(dates)} visits over {span} days - possible {cond}."))

    # 2. Accumulated allergies.
    if p["allergies"]:
        flags.append(("Allergies on record", ", ".join(p["allergies"])))

    # 3. Lab values: latest out of range, and worsening trend across visits.
    series = {}
    for e in encs:
        for lab in e["labs"]:
            series.setdefault(lab["test"], []).append((e["visit_date"], lab))
    for test, pts in series.items():
        when, last = pts[-1]
        lo, hi, v = last["ref_low"], last["ref_high"], last["value"]
        if v > hi or v < lo:
            side = "above" if v > hi else "below"
            flags.append(("Out-of-range lab",
                          f"{test} {v} {last['unit']} on {when} is {side} reference range ({lo}-{hi})."))
        vals = [lab["value"] for _, lab in pts]
        if len(vals) >= 2:
            rising = all(b > a for a, b in zip(vals, vals[1:]))
            falling = all(b < a for a, b in zip(vals, vals[1:]))
            if (rising and vals[-1] > hi) or (falling and vals[-1] < lo):
                trend = " -> ".join(map(str, vals))
                flags.append(("Worsening lab trend", f"{test} moved {trend} {last['unit']} across {len(vals)} visits."))

    # 4. Missed follow-ups: a due date (plus 14 days grace) has passed with no visit in between.
    visit_dates = [d(e["visit_date"]) for e in encs]
    for e in encs:
        for ins in e["instructions"]:
            if not ins["due_date"]:
                continue
            due = d(ins["due_date"])
            grace = due + timedelta(days=14)
            if grace < today and not any(d(e["visit_date"]) < v <= grace for v in visit_dates):
                flags.append(("Missed follow-up",
                              f"Follow-up due {due} (from {e['visit_date']} visit: {ins['text']}) - no visit recorded."))

    return [{"category": c, "detail": t, "label": REVIEW} for c, t in flags]
