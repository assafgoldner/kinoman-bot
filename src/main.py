"""
קינומן 🎬 — Flask server entry point.

Handles WhatsApp webhook verification (GET) and incoming messages (POST).
"""

import logging
import os

from flask import Flask, request

import message_handler
from config import VERIFY_TOKEN

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("kinoman")

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def webhook():
    """
    GET  → Webhook verification (Meta sends hub.mode, hub.verify_token, hub.challenge)
    POST → Incoming WhatsApp message
    """

    # ── GET: Webhook verification ──────────────────────────────────
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("Webhook verified successfully")
            return challenge, 200
        else:
            logger.warning("Webhook verification failed (token mismatch)")
            return "Forbidden", 403

    # ── POST: Incoming message ─────────────────────────────────────
    body = request.get_json(silent=True)
    if not body:
        return "OK", 200

    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for message in messages:
                    sender = message["from"]
                    logger.info(
                        "Message from %s: type=%s",
                        sender,
                        message.get("type"),
                    )
                    message_handler.handle(sender, message)

    except Exception:
        logger.error("Error processing webhook", exc_info=True)

    # Always return 200 — otherwise WhatsApp retries
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
