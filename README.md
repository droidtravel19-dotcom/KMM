# Law firm intake automation

Client enquiries (web form or inbox) → AI triage → acknowledgement reply → daily digest grouped by practice area.

```
web form ──POST /intake──┐
inbox ──cli poll (IMAP)──┴─► triage (Claude, keyword fallback) ─► SQLite
                                   │                                │
                          fixed-template auto-reply        digest by practice area
```

## Gmail (connector) mode - recommended
The Gmail connector is used by Claude, so the inbox work is a runbook: `.claude/skills/gmail-intake/SKILL.md`.
In a Claude session with the Gmail connector, say **"run intake"**. Claude will:
find new enquiry threads, triage them by practice area, store them via `python -m intake.cli prepare`,
**create draft** acknowledgement replies (never sends unless you say so), apply `Intake/<Practice area>`,
`Intake/Urgent` and `Intake/Processed` labels, and draft the digest (`python -m intake.cli digest --mark`).
No Gmail credentials or app passwords are stored in this repo. To automate it, schedule that prompt in Claude.

## WhatsApp
Meta's WhatsApp Business Cloud API posts incoming messages to `POST /whatsapp/webhook` (verified by `X-Hub-Signature-256`
using `WHATSAPP_APP_SECRET`; `GET` handles Meta's verify handshake with `WHATSAPP_VERIFY_TOKEN`). Text messages go through
the same triage and storage; the client gets the same fixed-template acknowledgement (free-form replies are allowed
within 24h of their message), at most once per sender per 24h. Like email, replies are drafts only until `SEND_REPLIES=true`.
Needs a Meta Business account, a WhatsApp Business number, a public HTTPS URL, and the four `WHATSAPP_*` values in `.env.example`.
Voice notes, images and documents are currently ignored. WhatsApp enquiries show in the digest with the phone number and no email.

## Standalone mode (IMAP/SMTP, no Claude in the loop)
```
pip install -r requirements.txt
cp .env.example .env   # fill in, then: set -a; . ./.env; set +a
uvicorn intake.app:app                 # POST /intake, GET /enquiries?practice_area=..., GET /digest
python -m intake.cli poll              # pull from inbox (cron every few minutes)
python -m intake.cli digest            # email the digest (cron daily)
pytest
```
`POST /intake` body: `{"name","email","phone","subject","message"}`; send `X-Intake-Token` if `INTAKE_TOKEN` is set.

## Design choices
- **Practice areas** (`intake/models.py`): Land & Conveyancing, Succession & Probate, Civil Litigation, Commercial, Family, Employment, Criminal, Other. Edit the enum + `KEYWORDS` to change them.
- **AI summary** returns summary, key facts, missing info, urgency and names of other parties (for conflict checks). If no API key is set, or the call/parse fails, a keyword classifier is used so no enquiry is dropped.
- **Auto-replies are fixed templates**, not model-written: no risk of accidental legal advice or prompt injection reaching clients. They state it is not legal advice and that no advocate-client relationship exists yet.
- **Safe by default**: `SEND_REPLIES=false` stores replies as drafts. Review a few, then switch to `true`.
- Urgent matters (arrest, eviction, hearing) are flagged `[URGENT]` and listed first in the digest.
- Duplicate emails are ignored (Message-ID); the firm's own address is never answered (loop guard).
- Enquiry data is confidential client information: keep `intake.db` on encrypted storage and review your Data Protection Act 2019 obligations (including sending text to an AI provider).
