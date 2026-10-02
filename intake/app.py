import hmac

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response

from . import db, digest, whatsapp
from .config import Settings
from .models import EnquiryIn
from .pipeline import process

settings = Settings()
conn = db.connect(settings.db_path)
app = FastAPI(title="Law firm intake")


def auth(x_intake_token: str = Header(default="")):
    if settings.intake_token and not hmac.compare_digest(x_intake_token, settings.intake_token):
        raise HTTPException(401, "bad token")


@app.post("/intake", dependencies=[Depends(auth)])
def intake(e: EnquiryIn):
    return process(conn, settings, e)


@app.get("/enquiries", dependencies=[Depends(auth)])
def enquiries(practice_area: str | None = None, limit: int = 100):
    return db.list_enquiries(conn, practice_area, min(limit, 500))


@app.get("/digest", dependencies=[Depends(auth)])
def get_digest():
    return {"text": digest.build_digest(db.undigested(conn))}


@app.post("/digest/send", dependencies=[Depends(auth)])
def post_digest():
    return {"text": digest.send_digest(conn, settings)}


@app.get("/whatsapp/webhook")
def wa_verify(mode: str = Query("", alias="hub.mode"), token: str = Query("", alias="hub.verify_token"),
              challenge: str = Query("", alias="hub.challenge")):
    if mode == "subscribe" and settings.wa_verify_token and hmac.compare_digest(token, settings.wa_verify_token):
        return Response(challenge, media_type="text/plain")
    raise HTTPException(403, "bad verify token")


@app.post("/whatsapp/webhook")
async def wa_receive(request: Request, x_hub_signature_256: str = Header(default="")):
    raw = await request.body()
    if not whatsapp.verify_signature(settings.wa_app_secret, raw, x_hub_signature_256):
        raise HTTPException(401, "bad signature")
    n = 0
    for e, wamid in whatsapp.parse_payload(await request.json()):
        # one acknowledgement per sender per 24h, even if they send several messages
        quiet = db.replied_recently(conn, e.phone)
        if process(conn, settings, e, message_id=wamid, reply=not quiet):
            n += 1
    return {"processed": n}  # always 200 so Meta does not retry
