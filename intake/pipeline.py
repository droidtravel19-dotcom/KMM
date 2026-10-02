from . import db, replies, triage as triage_mod, whatsapp
from .config import Settings
from .models import EnquiryIn, Triage


def process(conn, s: Settings, e: EnquiryIn, message_id: str | None = None, client=None, sender=None,
            preset: Triage | None = None, reply: bool = True) -> dict | None:
    t = triage_mod.triage(e, s, client=client)if preset is None else preset
    eid = db.save(conn, e, t, message_id)
    if eid is None:
        return None
    subject, body = replies.build_reply(e.name, t.practice_area.value, t.urgency.value, s)
    status = "none"
    if reply:
        if e.source == "whatsapp":
            status = replies.dispatch(s, e.phone, subject, body, sender or whatsapp.send_text)
        elif e.email:
            status = replies.dispatch(s, e.email, subject, body, sender or replies.send_email)
    db.set_reply(conn, eid, status, body)
    return {"id": eid, "reply_subject": subject, "reply_body": body, "practice_area": t.practice_area.value,
            "urgency": t.urgency.value, "summary": t.summary, "reply_status": status}
