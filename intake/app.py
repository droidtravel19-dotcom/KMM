import hmac

from fastapi import Depends, FastAPI, Header, HTTPException

from . import db, digest
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
