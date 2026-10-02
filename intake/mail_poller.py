"""Poll an IMAP inbox for unread enquiries and run them through the pipeline."""
import email
import imaplib
import logging
from email.header import decode_header, make_header
from email.utils import parseaddr

from . import db, pipeline
from .config import Settings
from .models import EnquiryIn

log = logging.getLogger(__name__)


def parse_message(raw: bytes) -> tuple[EnquiryIn, str]:
    m = email.message_from_bytes(raw)
    name, addr = parseaddr(m.get("From", ""))
    subject = str(make_header(decode_header(m.get("Subject", ""))))
    body = ""
    for part in m.walk():
        if part.get_content_type() == "text/plain" and not part.get_filename():
            body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
            break
    e = EnquiryIn(name=name or addr, email=addr, subject=subject[:300], message=(body.strip() or subject)[:20000], source="email")
    return e, m.get("Message-ID", "")


def poll_once(s: Settings, conn=None) -> int:
    conn = conn or db.connect(s.db_path)
    n = 0
    with imaplib.IMAP4_SSL(s.imap_host) as imap:
        imap.login(s.imap_user, s.imap_password)
        imap.select("INBOX")
        _, data = imap.search(None, "UNSEEN")
        for num in data[0].split():
            _, msg = imap.fetch(num, "(RFC822)")
            try:
                e, mid = parse_message(msg[0][1])
            except Exception:
                log.exception("skipping unparseable message %s", num)
                continue
            if e.email.lower() == s.reply_from.lower():
                continue  # never answer ourselves
            if pipeline.process(conn, s, e, message_id=mid or None):
                n += 1
    return n
