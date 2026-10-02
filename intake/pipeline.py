from . import db, replies, triage as triage_mod
from .config import Settings
from .models import EnquiryIn


def process(conn, s: Settings, e: EnquiryIn, message_id: str | None = None, client=None, sender=None) -> dict | None:
    t = triage_mod.triage(e, s, client=client)
    eid = db.save(conn, e, t, message_id)
    if eid is None:
        return None
    subject, body = replies.build_reply(e.name, t.practice_area.value, t.urgency.value, s)
    kw = {"sender": sender} if sender else {}
    status = replies.dispatch(s, e.email, subject, body, **kw)
    db.set_reply(conn, eid, status, body)
    return {"id": eid, "practice_area": t.practice_area.value, "urgency": t.urgency.value,
            "summary": t.summary, "reply_status": status}
