"""
Lakebase connection helper.
Reads the Postgres connection URL from a Databricks secret scope and provides
three query helpers used throughout the app.
"""

import base64
import datetime
import os
import uuid
from contextlib import contextmanager

import psycopg2
from databricks.sdk import WorkspaceClient
from psycopg2.extras import RealDictCursor

_w = WorkspaceClient()

_SCOPE = os.environ.get("LAKEBASE_SECRET_SCOPE", "database")
_KEY   = os.environ.get("LAKEBASE_SECRET_KEY",   "lakebase-url")


def _lakebase_url() -> str:
    secret = _w.secrets.get_secret(scope=_SCOPE, key=_KEY)
    return base64.b64decode(secret.value).decode("utf-8")


def _serialize(val):
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    return val


def _row(row) -> dict:
    return {k: _serialize(v) for k, v in dict(row).items()}


@contextmanager
def get_connection():
    conn = psycopg2.connect(_lakebase_url(), cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def run_query(sql: str, params=None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_row(r) for r in cur.fetchall()]


def run_write(sql: str, params=None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount


def run_returning(sql: str, params=None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = [_row(r) for r in cur.fetchall()]
            conn.commit()
            return rows
