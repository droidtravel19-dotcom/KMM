from collections import defaultdict

from . import db
from .config import Settings
from .models import PracticeArea
from .replies import dispatch


def build_digest(rows: list[dict]) -> str:
    if not rows:
        return "No new enquiries."
    by_area = defaultdict(list)
    for r in rows:
        by_area[r["practice_area"]].append(r)
    out = [f"{len(rows)} new enquir{'y' if len(rows) == 1 else 'ies'}\n"]
    for area in [a.value for a in PracticeArea]:
        items = by_area.get(area)
        if not items:
            continue
        out.append(f"== {area} ({len(items)}) ==")
        for r in sorted(items, key=lambda r: r["urgency"] != "high"):
            t = db.triage_of(r)
            flag = "[URGENT] " if r["urgency"] == "high" else ""
            out.append(f"#{r['id']} {flag}{r['name']} {('<' + r['email'] + '>') if r['email'] else ''} {r['phone']}".strip())
            out.append(f"  {t.summary}")
            if t.key_facts:
                out.append("  Facts: " + "; ".join(t.key_facts))
            if t.missing_info:
                out.append("  Ask: " + "; ".join(t.missing_info))
            if t.opposing_parties:
                out.append("  Conflict check: " + ", ".join(t.opposing_parties))
        out.append("")
    return "\n".join(out)


def send_digest(conn, s: Settings, sender=None) -> str:
    rows = db.undigested(conn)
    text = build_digest(rows)
    if rows and s.digest_to:
        kw = {"sender": sender} if sender else {}
        if dispatch(s, s.digest_to, "Intake digest by practice area", text, **kw) == "sent":
            db.mark_digested(conn, [r["id"] for r in rows])
    return text
