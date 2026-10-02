"""Auto-replies are fixed templates: no model-written text goes to clients,
so nothing can be mistaken for legal advice or steered by the enquiry content."""
import logging
import smtplib
from email.message import EmailMessage

from .config import Settings
from .models import Urgency

log = logging.getLogger(__name__)


def build_reply(name: str, area: str, urgency: str, s: Settings) -> tuple[str, str]:
    first = name.split()[0] if name.strip() else "there"
    urgent = ""
    if urgency == Urgency.HIGH.value:
        urgent = (f"\nYour message appears time-sensitive. Please call us on {s.firm_phone} "
                  "so that it can be handled immediately.\n" if s.firm_phone else
                  "\nYour message appears time-sensitive and has been flagged for priority review.\n")
    body = (
        f"Dear {first},\n\n"
        f"Thank you for contacting {s.firm_name}. We have received your enquiry and it has been "
        f"referred to our {area} team.\n{urgent}\n"
        "An advocate will review it and respond within one business day. To help us, please have ready any "
        "relevant documents (e.g. title documents, agreements, court papers, ID).\n\n"
        "Please note that this is an automated acknowledgement. It is not legal advice, and no "
        "advocate-client relationship exists until we confirm that we have accepted your instructions.\n\n"
        f"Kind regards,\n{s.firm_name}"
    )
    return f"We have received your enquiry - {s.firm_name}", body


def send_email(s: Settings, to: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.reply_from, to, subject
    msg.set_content(body)
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)


def dispatch(s: Settings, to: str, subject: str, body: str, sender=send_email) -> str:
    """Returns 'sent', 'draft' (SEND_REPLIES off) or 'failed'."""
    if not s.send_replies:
        log.info("DRAFT reply to %s: %s", to, subject)
        return "draft"
    try:
        sender(s, to, subject, body)
        return "sent"
    except Exception:
        log.exception("reply to %s failed", to)
        return "failed"
