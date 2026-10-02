"""python -m intake.cli poll    -> pull new enquiries from the inbox
   python -m intake.cli digest  -> email the digest grouped by practice area (run daily via cron)"""
import logging
import sys

from . import db, digest, mail_poller
from .config import Settings

logging.basicConfig(level=logging.INFO)
s = Settings()
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "poll":
    print(f"processed {mail_poller.poll_once(s)} enquiries")
elif cmd == "digest":
    print(digest.send_digest(db.connect(s.db_path), s))
else:
    sys.exit(__doc__)
