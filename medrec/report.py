"""HTML timeline + risk profile report per patient."""
from datetime import date, timedelta
from html import escape

CSS = """body{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#222}
h1{margin-bottom:0}.muted{color:#666}table{border-collapse:collapse;width:100%;margin:8px 0 16px}
td,th{border:1px solid #ddd;padding:6px 8px;text-align:left;font-size:14px}th{background:#f4f4f4}
.visit{border-left:4px solid #4a7bd0;padding:4px 12px;margin:12px 0}.flag{background:#fff6e0;border:1px solid #e8c36a;
padding:8px 12px;margin:6px 0;border-radius:4px}.tag{font-size:12px;font-weight:600;color:#8a5a00}
.hi{color:#b00020;font-weight:600}.banner{background:#eef3fb;padding:10px 12px;border-radius:4px}"""


def sparkline(vals, lo, hi, w=160, h=36):
    """Tiny inline SVG trend line with the reference range shaded."""
    top, bot = max(vals + [hi]), min(vals + [lo])
    span = (top - bot) or 1
    y = lambda v: h - 4 - (v - bot) / span * (h - 8)
    x = lambda i: 4 + i * (w - 8) / max(len(vals) - 1, 1)
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    return (f'<svg width="{w}" height="{h}"><rect x="0" y="{y(hi):.1f}" width="{w}" '
            f'height="{max(y(lo) - y(hi), 1):.1f}" fill="#e6f4ea"/>'
            f'<polyline points="{pts}" fill="none" stroke="#4a7bd0" stroke-width="2"/></svg>')


def render(p, flags, today=None):
    today = today or date.today()
    e_ = escape
    out = [f"<!doctype html><meta charset='utf-8'><title>{e_(p['name'])} - Record</title><style>{CSS}</style>",
           f"<h1>{e_(p['name'])}</h1><p class='muted'>Age {p['age']} &middot; Allergies: "
           f"{e_(', '.join(p['allergies']) or 'None recorded')} &middot; Generated {today}</p>",
           "<p class='banner'>Record-organization tool. Nothing here is a diagnosis; all flags are for doctor review.</p>"]

    # Risk profile
    out.append("<h2>Health risk profile</h2>")
    for f in flags or [{"category": "No flags", "detail": "No rule-based flags raised.", "label": "For doctor review"}]:
        out.append(f"<div class='flag'><span class='tag'>{e_(f['label']).upper()}</span> &middot; "
                   f"<b>{e_(f['category'])}</b><br>{e_(f['detail'])}</div>")

    # Medications: active = prescription window still open today
    rows = []
    for e in p["encounters"]:
        for m in e["meds"]:
            end = date.fromisoformat(e["visit_date"]) + timedelta(days=m["duration_days"])
            rows.append((e["visit_date"], m, end))
    active = {}
    for start, m, end in rows:  # latest prescription of each medicine wins
        active[m["name"]] = (start, m, end)
    active = [r for r in active.values() if r[2] >= today]
    out.append("<h2>Active medications</h2>")
    if active:
        out.append("<table><tr><th>Medicine</th><th>Dose</th><th>Frequency</th><th>Prescribed</th><th>Until</th></tr>")
        out += [f"<tr><td>{e_(m['name'])}</td><td>{e_(m['dose'])}</td><td>{e_(m['frequency'])}</td>"
                f"<td>{s}</td><td>{end}</td></tr>" for s, m, end in active]
        out.append("</table>")
    else:
        out.append("<p class='muted'>None active as of today.</p>")
    out.append("<h2>Medication history</h2><table><tr><th>Date</th><th>Medicine</th><th>Dose</th>"
               "<th>Frequency</th><th>Duration</th></tr>")
    out += [f"<tr><td>{s}</td><td>{e_(m['name'])}</td><td>{e_(m['dose'])}</td><td>{e_(m['frequency'])}</td>"
            f"<td>{m['duration_days']} days</td></tr>" for s, m, _ in rows]
    out.append("</table>")

    # Lab trends
    series = {}
    for e in p["encounters"]:
        for lab in e["labs"]:
            series.setdefault(lab["test"], []).append((e["visit_date"], lab))
    if series:
        out.append("<h2>Lab trends</h2><table><tr><th>Test</th><th>Values over time</th><th>Range</th><th>Trend</th></tr>")
        for test, pts in series.items():
            lo, hi, unit = pts[-1][1]["ref_low"], pts[-1][1]["ref_high"], pts[-1][1]["unit"]
            vals = " &rarr; ".join(
                f"<span class='{'hi' if not lo <= l['value'] <= hi else ''}'>{l['value']}</span> "
                f"<span class='muted'>({dt})</span>" for dt, l in pts)
            spark = sparkline([l["value"] for _, l in pts], lo, hi)
            out.append(f"<tr><td>{e_(test)}</td><td>{vals}</td><td>{lo}-{hi} {e_(unit)}</td><td>{spark}</td></tr>")
        out.append("</table>")

    # Visit timeline
    out.append("<h2>Visit timeline</h2>")
    for e in p["encounters"]:
        meds = ", ".join(f"{m['name']} {m['dose']}" for m in e["meds"]) or "None"
        labs = ", ".join(f"{l['test']} {l['value']} {l['unit']}" for l in e["labs"]) or "None"
        fu = "; ".join(f"{i['text']} (by {i['due_date']})" for i in e["instructions"]) or "None"
        out.append(f"<div class='visit'><b>{e['visit_date']}</b> &middot; {e_(e['record_type'].replace('_', ' '))} "
                   f"&middot; {e_(e['doctor'])}<br><b>Diagnosis:</b> {e_(e['diagnosis'])}<br>"
                   f"<b>Medicines:</b> {e_(meds)}<br><b>Labs:</b> {e_(labs)}<br><b>Follow-up:</b> {e_(fu)}<br>"
                   f"<span class='muted'>Source: {e_(e['source_file'])}</span></div>")
    return "\n".join(out)
