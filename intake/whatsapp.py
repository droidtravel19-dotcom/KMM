"""WhatsApp Business Cloud API (Meta) webhook + replies.

Setup: Meta developer app -> WhatsApp product -> webhook URL https://<host>/whatsapp/webhook,
verify token = WHATSAPP_VERIFY_TOKEN, subscribe to `messages`. A free-form reply is only allowed
within 24h of the client's message, which is exactly when our acknowledgement goes out.
"""
import hashlib
import hmac

import httpx

from .config import Settings
from .models import EnquiryIn

GRAPH = "https://graph.facebook.com/v20.0"


def verify_signature(secret: str, body: bytes, header: str) -> bool:
    if not secret:
        return False  # refuse unsigned traffic unless an app secret is configured
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")


def parse_payload(payload: dict) -> list[tuple[EnquiryIn, str]]:
    """Text messages only -> [(enquiry, wamid)]. Media/other types are ignored."""
    out = []
    for entry in payload.get("entry", []):
        for ch in entry.get("changes", []):
            v = ch.get("value", {})
            names = {c.get("wa_id"): c.get("profile", {}).get("name", "") for c in v.get("contacts", [])}
            for m in v.get("messages", []):
                if m.get("type") != "text":
                    continue
                phone = m["from"]
                text = m["text"]["body"].strip()
                if not text:
                    continue
                out.append((EnquiryIn(name=names.get(phone) or phone, phone="+" + phone.lstrip("+"),
                                      subject="WhatsApp enquiry", message=text[:20000], source="whatsapp"), m["id"]))
    return out


def send_text(s: Settings, to: str, subject: str, body: str):
    r = httpx.post(f"{GRAPH}/{s.wa_phone_number_id}/messages", timeout=30,
                   headers={"Authorization": f"Bearer {s.wa_token}"},
                   json={"messaging_product": "whatsapp", "to": to.lstrip("+"), "type": "text", "text": {"body": body}})
    r.raise_for_status()
