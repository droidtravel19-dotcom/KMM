from types import SimpleNamespace

from intake import db, digest, pipeline
from intake.config import Settings
from intake.mail_poller import parse_message
from intake.models import EnquiryIn, PracticeArea
from intake.triage import keyword_triage

S = Settings(anthropic_api_key="", send_replies=False, firm_name="Test LLP", digest_to="p@x.com")


def enq(msg, **kw):
    return EnquiryIn(name="Jane Wanjiku", email="jane@example.com", message=msg, **kw)


def test_keyword_areas():
    assert keyword_triage(enq("I want to buy a plot and need the title deed transferred")).practice_area == PracticeArea.LAND
    assert keyword_triage(enq("My late father left no will, need letters of administration")).practice_area == PracticeArea.SUCCESSION
    assert keyword_triage(enq("hello")).practice_area == PracticeArea.OTHER


def test_urgency():
    assert keyword_triage(enq("My brother was arrested and needs bail")).urgency.value == "high"
    assert keyword_triage(enq("Want to incorporate a company")).urgency.value == "normal"


def test_ai_path_and_bad_json_fallback():
    good = SimpleNamespace(content=[SimpleNamespace(type="text", text='x {"practice_area":"Criminal","urgency":"high","summary":"s","key_facts":["a"],"missing_info":[],"opposing_parties":["DPP"]} y')])
    bad = SimpleNamespace(content=[SimpleNamespace(type="text", text="sorry")])
    mk = lambda r: SimpleNamespace(messages=SimpleNamespace(create=lambda **k: r))
    from intake.triage import triage
    t = triage(enq("x"), S, client=mk(good))
    assert t.method == "ai" and t.practice_area == PracticeArea.CRIMINAL
    assert triage(enq("land plot"), S, client=mk(bad)).method == "keyword"


def test_pipeline_reply_dedupe_digest():
    conn = db.connect(":memory:")
    r = pipeline.process(conn, S, enq("title deed for my plot"), message_id="<1>")
    assert r["reply_status"] == "draft" and r["practice_area"] == "Land & Conveyancing"
    assert pipeline.process(conn, S, enq("title deed"), message_id="<1>") is None
    row = db.list_enquiries(conn)[0]
    assert "not legal advice" in row["reply_body"] and "Jane" in row["reply_body"]
    assert "== Land & Conveyancing (1) ==" in digest.build_digest(db.undigested(conn))


def test_send_and_failure_status():
    sent = []
    on = Settings(send_replies=True, anthropic_api_key="")
    conn = db.connect(":memory:")
    assert pipeline.process(conn, on, enq("divorce"), sender=lambda *a: sent.append(a))["reply_status"] == "sent"
    def boom(*a): raise OSError
    assert pipeline.process(conn, on, enq("divorce 2"), sender=boom)["reply_status"] == "failed"


def test_digest_marks_only_when_sent():
    conn = db.connect(":memory:")
    pipeline.process(conn, S, enq("plot"))
    digest.send_digest(conn, S)
    assert len(db.undigested(conn)) == 1  # drafts don't consume the queue
    sent = []
    digest.send_digest(conn, Settings(send_replies=True, digest_to="p@x.com"), sender=lambda *a: sent.append(a))
    assert sent and not db.undigested(conn)


def test_parse_email():
    raw = b"From: Jo K <jo@x.com>\nSubject: Land dispute\nMessage-ID: <abc>\nContent-Type: text/plain\n\nBoundary dispute on my plot."
    e, mid = parse_message(raw)
    assert e.email == "jo@x.com" and mid == "<abc>" and "Boundary" in e.message


def test_api(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("INTAKE_TOKEN", "sekret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from fastapi.testclient import TestClient
    from intake import app as appmod
    import importlib
    importlib.reload(appmod)
    c = TestClient(appmod.app)
    body = {"name": "A B", "email": "a@b.com", "message": "unfair dismissal from my employer"}
    assert c.post("/intake", json=body).status_code == 401
    r = c.post("/intake", json=body, headers={"x-intake-token": "sekret"})
    assert r.json()["practice_area"] == "Employment & Labour"
    assert c.get("/enquiries", headers={"x-intake-token": "sekret"}).json()[0]["name"] == "A B"


def test_prepare_uses_claude_triage_and_never_sends():
    from intake.cli import prepare
    conn = db.connect(":memory:")
    on = Settings(send_replies=True, anthropic_api_key="")
    item = lambda: {"name": "Jo K", "email": "jo@x.com", "subject": "help", "message": "m", "thread_id": "T1",
                    "triage": {"practice_area": "Criminal", "urgency": "high", "summary": "s"}}
    r = prepare(on, [item()], conn)[0]
    assert r["practice_area"] == "Criminal" and r["reply_status"] == "draft" and "reply_body" in r
    assert prepare(on, [item()], conn)[0]["duplicate"] is True


def _wa_payload(*texts, phone="254712345678"):
    msgs = [{"from": phone, "id": f"wamid.{i}", "type": "text", "text": {"body": t}} for i, t in enumerate(texts)]
    msgs.append({"from": phone, "id": "wamid.img", "type": "image"})
    return {"entry": [{"changes": [{"value": {"contacts": [{"wa_id": phone, "profile": {"name": "Peter M"}}], "messages": msgs}}]}]}


def test_whatsapp_parse_and_signature():
    import hashlib, hmac
    from intake import whatsapp
    items = whatsapp.parse_payload(_wa_payload("I need help with my plot"))
    assert len(items) == 1 and items[0][0].phone == "+254712345678" and items[0][0].email is None
    sig = "sha256=" + hmac.new(b"k", b"body", hashlib.sha256).hexdigest()
    assert whatsapp.verify_signature("k", b"body", sig)
    assert not whatsapp.verify_signature("k", b"body", "sha256=bad") and not whatsapp.verify_signature("", b"body", sig)


def test_whatsapp_webhook(tmp_path, monkeypatch):
    import hashlib, hmac, json
    monkeypatch.setenv("DB_PATH", str(tmp_path / "w.db"))
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "vt")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "sec")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.delenv("SEND_REPLIES", raising=False)
    from fastapi.testclient import TestClient
    from intake import app as appmod
    import importlib
    importlib.reload(appmod)
    c = TestClient(appmod.app)
    assert c.get("/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "42"}).text == "42"
    assert c.get("/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "42"}).status_code == 403
    raw = json.dumps(_wa_payload("my land title dispute", "please call me")).encode()
    sig = "sha256=" + hmac.new(b"sec", raw, hashlib.sha256).hexdigest()
    assert c.post("/whatsapp/webhook", content=raw, headers={"x-hub-signature-256": "sha256=0"}).status_code == 401
    assert c.post("/whatsapp/webhook", content=raw, headers={"x-hub-signature-256": sig}).json() == {"processed": 2}
    from intake import db
    rows = db.list_enquiries(appmod.conn)
    assert sorted(r["reply_status"] for r in rows) == ["draft", "none"]  # one ack for two messages
    assert c.post("/whatsapp/webhook", content=raw, headers={"x-hub-signature-256": sig}).json() == {"processed": 0}  # redelivery deduped
