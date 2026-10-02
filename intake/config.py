import os
from dataclasses import dataclass, field


def _b(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes"}


@dataclass
class Settings:
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    triage_model: str = field(default_factory=lambda: os.getenv("TRIAGE_MODEL", "claude-sonnet-5-5"))
    firm_name: str = field(default_factory=lambda: os.getenv("FIRM_NAME", "Kahiga Mukami & Macharia Advocates"))
    firm_phone: str = field(default_factory=lambda: os.getenv("FIRM_PHONE", ""))
    reply_from: str = field(default_factory=lambda: os.getenv("REPLY_FROM", ""))
    digest_to: str = field(default_factory=lambda: os.getenv("DIGEST_TO", ""))
    send_replies: bool = field(default_factory=lambda: _b("SEND_REPLIES"))
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    imap_host: str = field(default_factory=lambda: os.getenv("IMAP_HOST", ""))
    imap_user: str = field(default_factory=lambda: os.getenv("IMAP_USER", ""))
    imap_password: str = field(default_factory=lambda: os.getenv("IMAP_PASSWORD", ""))
    intake_token: str = field(default_factory=lambda: os.getenv("INTAKE_TOKEN", ""))
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "intake.db"))
    wa_token: str = field(default_factory=lambda: os.getenv("WHATSAPP_TOKEN", ""))
    wa_phone_number_id: str = field(default_factory=lambda: os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""))
    wa_verify_token: str = field(default_factory=lambda: os.getenv("WHATSAPP_VERIFY_TOKEN", ""))
    wa_app_secret: str = field(default_factory=lambda: os.getenv("WHATSAPP_APP_SECRET", ""))
