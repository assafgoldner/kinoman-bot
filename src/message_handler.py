"""
Message handler — routes incoming WhatsApp messages, detects fuzzy matches,
manages user sessions for multi-step flows (e.g., "which movie did you mean?").
"""

import logging
from datetime import datetime, timedelta

import movie_client
import whatsapp_client

logger = logging.getLogger("kinoman.handler")

# ── In-memory session store ─────────────────────────────────────────
# Maps sender phone → {"options": [...], "timestamp": "..."}
# In production, replace with Redis / Firestore for persistence.
_sessions: dict[str, dict] = {}

# Auto-expire sessions after 10 minutes
SESSION_TTL = timedelta(minutes=10)


def _cleanup_session(sender: str) -> None:
    """Remove expired session."""
    session = _sessions.get(sender)
    if session:
        ts = datetime.fromisoformat(session["timestamp"])
        if datetime.utcnow() - ts > SESSION_TTL:
            del _sessions[sender]


# ── Handler: Interactive button/list reply ──────────────────────────

def _handle_interactive(sender: str, message: dict) -> None:
    """Handle when user taps a button or list item."""
    interactive = message.get("interactive", {})
    reply_type = interactive.get("type")

    selected_id = None
    if reply_type == "button_reply":
        selected_id = interactive["button_reply"]["id"]
    elif reply_type == "list_reply":
        selected_id = interactive["list_reply"]["id"]

    if selected_id and sender in _sessions:
        session = _sessions[sender]
        for opt in session.get("options", []):
            if opt["id"] == selected_id:
                # User chose a movie — get full details
                details = movie_client.get_movie_details(opt["tmdb_id"])
                if details:
                    response = movie_client.format_movie_response(details)
                else:
                    response = "מצטער, לא הצלחתי למצוא מידע על הסרט. נסה שוב 🙏"
                whatsapp_client.send_text(sender, response)
                del _sessions[sender]
                return

    whatsapp_client.send_text(sender, "לא הבנתי את הבחירה. נסה שוב 🙏")


# ── Handler: Text message ──────────────────────────────────────────

def _handle_text(sender: str, message: dict) -> None:
    """Handle a text message — movie name or plot description."""
    user_text = message["text"]["body"].strip()

    # Check if it's a simple number reply to a pending fuzzy match
    if sender in _sessions and user_text in ("1", "2", "3"):
        session = _sessions[sender]
        idx = int(user_text) - 1
        options = session.get("options", [])
        if idx < len(options):
            details = movie_client.get_movie_details(options[idx]["tmdb_id"])
            if details:
                response = movie_client.format_movie_response(details)
            else:
                response = "מצטער, לא הצלחתי למצוא מידע על הסרט. נסה שוב 🙏"
            whatsapp_client.send_text(sender, response)
            del _sessions[sender]
            return

    # Search for movies — try direct title search first
    results = movie_client.search_movie(user_text)

    # If no results and text looks like a description, use LLM to guess
    if not results and movie_client.is_description(user_text):
        guesses = movie_client.guess_movie_from_description(user_text)
        for guess in guesses:
            results = movie_client.search_movie(guess)
            if results:
                break

    if not results:
        whatsapp_client.send_text(
            sender,
            "לא מצאתי סרט מתאים. נסה לתאר אחרת או לחפש בשם 🙏",
        )
        return

    if len(results) == 1:
        # Single match — show full details
        details = movie_client.get_movie_details(results[0]["id"])
        if details:
            whatsapp_client.send_text(
                sender, movie_client.format_movie_response(details)
            )
        else:
            whatsapp_client.send_text(
                sender, "מצטער, לא הצלחתי למצוא מידע על הסרט. נסה שוב 🙏"
            )
        return

    # Multiple matches — present options
    options = []
    seen_titles = set()
    for i, r in enumerate(results[:3]):
        title_display = r["title"]
        if r["original_title"] and r["original_title"] != r["title"]:
            title_display = f"{r['title']} / {r['original_title']}"
        year_suffix = f" ({r['year']})" if r["year"] else ""

        # Ensure unique button titles (WhatsApp rejects duplicates)
        btn_title = r["title"][:20]
        if btn_title in seen_titles and r["year"]:
            btn_title = f"{r['title'][:15]} ({r['year']})"[:20]
        seen_titles.add(btn_title)

        options.append({
            "id": f"option_{i + 1}",
            "title": btn_title,
            "full_text": f"{title_display}{year_suffix}",
            "tmdb_id": r["id"],
        })

    # Store session
    _sessions[sender] = {
        "options": options,
        "timestamp": datetime.utcnow().isoformat(),
    }

    body_text = "מצאתי כמה אפשרויות — למה התכוונת?"

    if len(options) <= 3:
        whatsapp_client.send_buttons(
            sender,
            body_text,
            [{"id": opt["id"], "title": opt["title"]} for opt in options],
        )
    else:
        whatsapp_client.send_list(
            sender,
            body_text,
            "בחר סרט",
            [{"id": opt["id"], "title": opt["title"]} for opt in options],
        )


# ── Main entry point ────────────────────────────────────────────────

def handle(sender: str, message: dict) -> None:
    """
    Route an incoming WhatsApp message to the appropriate handler.

    Supports: text, interactive (button/list reply).
    """
    _cleanup_session(sender)
    msg_type = message.get("type")

    if msg_type == "interactive":
        _handle_interactive(sender, message)
    elif msg_type == "text":
        _handle_text(sender, message)
    else:
        whatsapp_client.send_text(
            sender,
            "אני עובד עם טקסט בלבד 📝\n"
            "שלח לי שם סרט או תיאור עלילה!",
        )
