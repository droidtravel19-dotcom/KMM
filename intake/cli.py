"""Commands (Claude drives Gmail through the connector; see .claude/skills/gmail-intake/SKILL.md):

  python -m intake.cli prepare < enquiries.json   store enquiries, print reply drafts as JSON
  python -m intake.cli digest [--mark]            print the digest of un-digested enquiries
  python -m intake.cli poll                       (alternative) pull from an IMAP inbox
"""
import json
import logging
import sys

from . import db, digest, mail_poller, pipeline
from .config import Settings
from .models import EnquiryIn, Triage

logging.basicConfig(level=logging.INFO, stream=sys.stderr)


def prepare(s: Settings, items: list[dict], conn=None) -> list[dict]:
    """items: [{name,email,subject,message,thread_id,triage?}]. A `triage` object (made by Claude
    in-session) is used as-is; otherwise the Python triage runs. Replies are never sent from here."""
    conn = conn or db.connect(s.db_path)
    s.send_replies = False
    out = []
    for it in items:
        tid = it.pop("thread_id", None)
        preset = it.pop("triage", None)
        e = EnquiryIn(**it, source="gmail")
        r = pipeline.process(conn, s, e, message_id=tid, preset=Triage(**{**preset, "method": "claude"}) if preset else None)
        out.append({"thread_id": tid, "to": e.email, **(r or {"duplicate": True})})
    return out


if __name__ == "__main__":
    s = Settings()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "prepare":
        print(json.dumps(prepare(s, json.load(sys.stdin)), indent=2))
    elif cmd == "digest":
        conn = db.connect(s.db_path)
        rows = db.undigested(conn)
        print(digest.build_digest(rows))
        if "--mark" in sys.argv:
            db.mark_digested(conn, [r["id"] for r in rows])
    elif cmd == "poll":
        print(f"processed {mail_poller.poll_once(s)} enquiries")
    else:
        sys.exit(__doc__)
