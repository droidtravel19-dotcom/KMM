import json
import sqlite3
from datetime import datetime, timezone

from .models import EnquiryIn, Triage

SCHEMA = """
CREATE TABLE IF NOT EXISTS enquiries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  received_at TEXT NOT NULL,
  name TEXT, email TEXT, phone TEXT, subject TEXT, message TEXT, source TEXT,
  practice_area TEXT, urgency TEXT, summary TEXT, triage_json TEXT,
  reply_status TEXT DEFAULT 'none',   -- none | draft | sent | failed
  reply_body TEXT,
  digested INTEGER DEFAULT 0,
  message_id TEXT UNIQUE              -- dedupe for polled email
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save(conn, e: EnquiryIn, t: Triage, message_id: str | None = None) -> int | None:
    try:
        cur = conn.execute(
            "INSERT INTO enquiries (received_at,name,email,phone,subject,message,source,practice_area,urgency,summary,triage_json,message_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), e.name, e.email, e.phone, e.subject, e.message, e.source,
             t.practice_area.value, t.urgency.value, t.summary, t.model_dump_json(), message_id),
        )
    except sqlite3.IntegrityError:
        return None  # already processed
    conn.commit()
    return cur.lastrowid


def set_reply(conn, enquiry_id: int, status: str, body: str):
    conn.execute("UPDATE enquiries SET reply_status=?, reply_body=? WHERE id=?", (status, body, enquiry_id))
    conn.commit()


def list_enquiries(conn, area: str | None = None, limit: int = 100):
    q, args = "SELECT * FROM enquiries", []
    if area:
        q += " WHERE practice_area=?"
        args.append(area)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(q, args)]


def undigested(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM enquiries WHERE digested=0 ORDER BY id")]


def mark_digested(conn, ids: list[int]):
    conn.executemany("UPDATE enquiries SET digested=1 WHERE id=?", [(i,) for i in ids])
    conn.commit()


def triage_of(row: dict) -> Triage:
    return Triage(**json.loads(row["triage_json"]))
