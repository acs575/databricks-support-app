"""
One-time setup script — creates the Lakebase schema and seeds sample data.
Safe to re-run: uses CREATE TABLE IF NOT EXISTS and ON CONFLICT DO NOTHING.

Run from a Databricks notebook cell:
    %run /Users/<you>/databricks-support-app/setup_db
Or execute directly as a Python file.
"""

import base64
import os

import psycopg2
from databricks.sdk import WorkspaceClient
from psycopg2.extras import RealDictCursor

# ── Connection ────────────────────────────────────────────────────────────────

_w = WorkspaceClient()
_secret = _w.secrets.get_secret(scope="database", key="lakebase-url")
_URL = base64.b64decode(_secret.value).decode("utf-8")


def _conn():
    return psycopg2.connect(_URL, cursor_factory=RealDictCursor)


# ── Schema ────────────────────────────────────────────────────────────────────

def create_tables():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                    title      TEXT        NOT NULL,
                    status     TEXT        NOT NULL DEFAULT 'open'
                                          CHECK (status IN ('open','in_progress','resolved')),
                    priority   TEXT        NOT NULL DEFAULT 'medium'
                                          CHECK (priority IN ('low','medium','high')),
                    category   TEXT        NOT NULL DEFAULT 'question'
                                          CHECK (category IN ('bug','feature','question')),
                    created_by TEXT        NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    message_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                    ticket_id    UUID        NOT NULL
                                            REFERENCES tickets(ticket_id)
                                            ON DELETE CASCADE,
                    message_text TEXT        NOT NULL,
                    author       TEXT        NOT NULL,
                    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
        conn.commit()
    print("Tables created (or already exist).")


# ── Sample data ───────────────────────────────────────────────────────────────

TICKETS = [
    ("a0000001-0000-0000-0000-000000000001",
     "App crashes on login with SSO", "open", "high", "bug",
     "alice@example.com"),
    ("a0000001-0000-0000-0000-000000000002",
     "Add dark mode to the dashboard", "in_progress", "low", "feature",
     "bob@example.com"),
    ("a0000001-0000-0000-0000-000000000003",
     "How do I export data to CSV?", "resolved", "medium", "question",
     "carol@example.com"),
    ("a0000001-0000-0000-0000-000000000004",
     "Pipeline fails with OOM on large datasets", "open", "high", "bug",
     "dave@example.com"),
    ("a0000001-0000-0000-0000-000000000005",
     "Integrate Slack notifications for alerts", "in_progress", "medium", "feature",
     "alice@example.com"),
]

MESSAGES = [
    # Ticket 1
    ("a0000001-0000-0000-0000-000000000001",
     "This started happening after the SSO update on Monday. All SSO users are affected.",
     "alice@example.com"),
    ("a0000001-0000-0000-0000-000000000001",
     "Can you share the browser console logs? Does it affect all browsers?",
     "support@example.com"),
    ("a0000001-0000-0000-0000-000000000001",
     "Confirmed — Chrome only. Firefox works fine. Attaching console logs now.",
     "alice@example.com"),
    # Ticket 2
    ("a0000001-0000-0000-0000-000000000002",
     "Dark mode is on the Q3 roadmap. We are currently in the design phase.",
     "support@example.com"),
    ("a0000001-0000-0000-0000-000000000002",
     "Is there a beta I can join to test early?",
     "bob@example.com"),
    # Ticket 3
    ("a0000001-0000-0000-0000-000000000003",
     "Go to Settings > Export > CSV. You can filter by date range before exporting.",
     "support@example.com"),
    ("a0000001-0000-0000-0000-000000000003",
     "That worked perfectly, thank you!",
     "carol@example.com"),
    # Ticket 4
    ("a0000001-0000-0000-0000-000000000004",
     "OOM occurs at the join step with 10M+ rows. Cluster is m5.4xlarge, 32 GB RAM.",
     "dave@example.com"),
    ("a0000001-0000-0000-0000-000000000004",
     "Try setting spark.sql.shuffle.partitions=400 and use broadcast join for the smaller table.",
     "support@example.com"),
    # Ticket 5
    ("a0000001-0000-0000-0000-000000000005",
     "We use Slack for all team alerts. A webhook integration would save us a lot of manual work.",
     "alice@example.com"),
    ("a0000001-0000-0000-0000-000000000005",
     "We are building a generic webhook framework — Slack will be the first supported target.",
     "support@example.com"),
]


def seed_data():
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM tickets")
            count = cur.fetchone()["cnt"]
            if count > 0:
                print(f"Sample data already present ({count} tickets). Skipping seed.")
                return

            cur.executemany(
                """
                INSERT INTO tickets (ticket_id, title, status, priority, category, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticket_id) DO NOTHING
                """,
                TICKETS,
            )
            cur.executemany(
                """
                INSERT INTO ticket_messages (ticket_id, message_text, author)
                VALUES (%s, %s, %s)
                """,
                MESSAGES,
            )
        conn.commit()
    print(f"Seeded {len(TICKETS)} tickets and {len(MESSAGES)} messages.")


# ── Entry point ───────────────────────────────────────────────────────────────

create_tables()
seed_data()
print("Setup complete.")
