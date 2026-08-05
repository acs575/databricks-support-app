"""
Internal support ticket system — Flask backend.
All data is stored in and read from Lakebase (Databricks-managed Postgres).
"""

import logging
import os

from databricks.sdk import WorkspaceClient
from flask import Flask, jsonify, render_template, request

import lakebase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("support-app")

app = Flask(__name__)
_w = WorkspaceClient()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_user() -> str:
    """
    Resolve the logged-in user’s email.
    Databricks Apps inject X-Forwarded-Email on every request.
    Falls back to the SDK for local development.
    """
    email = request.headers.get("X-Forwarded-Email")
    if email:
        return email
    return _w.current_user.me().user_name


@app.errorhandler(Exception)
def handle_exception(err):
    """Return all unhandled errors as JSON so the frontend never sees raw HTML."""
    logger.exception("Unhandled exception")
    code = getattr(err, "code", 500)
    if not isinstance(code, int):
        code = 500
    return jsonify({"error": str(err)}), code


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------

@app.route("/tickets", methods=["GET"])
def list_tickets():
    """Return all tickets, optionally filtered by ?status=open|in_progress|resolved."""
    status = request.args.get("status", "").strip()
    valid_statuses = ("open", "in_progress", "resolved")
    if status and status not in valid_statuses:
        return jsonify({"error": f"status must be one of: {', '.join(valid_statuses)}"}), 400

    if status:
        rows = lakebase.run_query(
            "SELECT * FROM tickets WHERE status = %s ORDER BY created_at DESC",
            (status,),
        )
    else:
        rows = lakebase.run_query(
            "SELECT * FROM tickets ORDER BY created_at DESC"
        )
    return jsonify(rows)


@app.route("/tickets", methods=["POST"])
def create_ticket():
    """Create a new ticket. Returns the created row."""
    data = request.get_json() or {}
    title    = (data.get("title")    or "").strip()
    priority = (data.get("priority") or "medium").strip()
    category = (data.get("category") or "question").strip()

    # Validation
    if not title:
        return jsonify({"error": "Title is required."}), 400
    if len(title) > 200:
        return jsonify({"error": "Title must be 200 characters or fewer."}), 400
    if priority not in ("low", "medium", "high"):
        return jsonify({"error": "Priority must be low, medium, or high."}), 400
    if category not in ("bug", "feature", "question"):
        return jsonify({"error": "Category must be bug, feature, or question."}), 400

    created_by = _current_user()
    rows = lakebase.run_returning(
        """
        INSERT INTO tickets (title, status, priority, category, created_by)
        VALUES (%s, 'open', %s, %s, %s)
        RETURNING *
        """,
        (title, priority, category, created_by),
    )
    return jsonify(rows[0]), 201


@app.route("/tickets/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    """Return one ticket and all its messages."""
    tickets = lakebase.run_query(
        "SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,)
    )
    if not tickets:
        return jsonify({"error": "Ticket not found."}), 404

    messages = lakebase.run_query(
        "SELECT * FROM ticket_messages WHERE ticket_id = %s ORDER BY created_at ASC",
        (ticket_id,),
    )
    ticket = tickets[0]
    ticket["messages"] = messages
    return jsonify(ticket)


@app.route("/tickets/<ticket_id>/status", methods=["PATCH"])
def update_status(ticket_id):
    """Update the status of a ticket."""
    data   = request.get_json() or {}
    status = (data.get("status") or "").strip()

    if status not in ("open", "in_progress", "resolved"):
        return jsonify({"error": "Status must be open, in_progress, or resolved."}), 400

    rows = lakebase.run_returning(
        "UPDATE tickets SET status = %s WHERE ticket_id = %s RETURNING ticket_id, status",
        (status, ticket_id),
    )
    if not rows:
        return jsonify({"error": "Ticket not found."}), 404
    return jsonify(rows[0])


@app.route("/tickets/<ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):
    """
    Delete a ticket and all its messages (CASCADE is defined on the FK).
    Returns the deleted ticket_id for confirmation.
    """
    rows = lakebase.run_returning(
        "DELETE FROM tickets WHERE ticket_id = %s RETURNING ticket_id",
        (ticket_id,),
    )
    if not rows:
        return jsonify({"error": "Ticket not found."}), 404
    return jsonify({"deleted": rows[0]["ticket_id"]})


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@app.route("/tickets/<ticket_id>/messages", methods=["POST"])
def add_message(ticket_id):
    """Add a message to an existing ticket."""
    exists = lakebase.run_query(
        "SELECT 1 FROM tickets WHERE ticket_id = %s", (ticket_id,)
    )
    if not exists:
        return jsonify({"error": "Ticket not found."}), 404

    data = request.get_json() or {}
    text = (data.get("message_text") or "").strip()

    if not text:
        return jsonify({"error": "Message text is required."}), 400
    if len(text) > 2000:
        return jsonify({"error": "Message must be 2 000 characters or fewer."}), 400

    author = _current_user()
    rows = lakebase.run_returning(
        """
        INSERT INTO ticket_messages (ticket_id, message_text, author)
        VALUES (%s, %s, %s)
        RETURNING *
        """,
        (ticket_id, text, author),
    )
    return jsonify(rows[0]), 201


# ---------------------------------------------------------------------------
# Stats  (bonus)
# ---------------------------------------------------------------------------

@app.route("/stats", methods=["GET"])
def get_stats():
    """Return aggregate statistics for the dashboard header."""
    total       = lakebase.run_query("SELECT COUNT(*) AS n FROM tickets")[0]["n"]
    by_status   = lakebase.run_query(
        "SELECT status, COUNT(*) AS n FROM tickets GROUP BY status"
    )
    by_priority = lakebase.run_query(
        "SELECT priority, COUNT(*) AS n FROM tickets GROUP BY priority"
    )
    avg_row     = lakebase.run_query(
        """
        SELECT ROUND(AVG(c)::numeric, 1) AS avg
        FROM (SELECT COUNT(*) AS c FROM ticket_messages GROUP BY ticket_id) sub
        """
    )
    return jsonify({
        "total_tickets":           total,
        "by_status":               {r["status"]:   r["n"] for r in by_status},
        "by_priority":             {r["priority"]: r["n"] for r in by_priority},
        "avg_messages_per_ticket": float(avg_row[0]["avg"] or 0) if avg_row else 0.0,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
