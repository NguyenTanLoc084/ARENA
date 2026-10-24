"""Lộc: connections, schema, transaction boundaries. Never commit inside services."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from flask import g, current_app


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"], timeout=15, isolation_level=None
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA busy_timeout=15000")
    return g.db


def close_db(_=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    rows = get_db().execute(sql, args).fetchall()
    return (rows[0] if rows else None) if one else rows


@contextmanager
def transaction():
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    else:
        db.commit()


def audit(db, user, action, entity, detail=""):
    db.execute(
        "INSERT INTO audit(user_id,action,entity,detail,created) VALUES(?,?,?,?,?)",
        (user["id"], action, str(entity), detail, now()),
    )


def notify(db, user_id, message):
    db.execute(
        "INSERT INTO notifications(user_id,message,created) VALUES(?,?,?)",
        (user_id, message, now()),
    )
