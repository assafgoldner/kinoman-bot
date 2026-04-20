"""
WhatsApp Cloud API client — sending messages, buttons, and lists.
"""

import logging
import requests

from config import (
    WHATSAPP_TOKEN,
    WHATSAPP_API_URL,
    WHATSAPP_MAX_MESSAGE_LENGTH,
    WHATSAPP_MAX_BUTTON_TITLE,
    WHATSAPP_MAX_BUTTONS,
    WHATSAPP_MAX_LIST_ITEMS,
)

logger = logging.getLogger("kinoman.whatsapp")


# ── Low-level API call ──────────────────────────────────────────────

def _send(payload: dict) -> requests.Response:
    """Send a payload to WhatsApp Cloud API."""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    resp = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        logger.error("WhatsApp API error: %s — %s", resp.status_code, resp.text)
    return resp


# ── Message helpers ─────────────────────────────────────────────────

def _split_message(text: str, max_len: int = WHATSAPP_MAX_MESSAGE_LENGTH) -> list[str]:
    """Split a long message at line breaks to stay within WhatsApp limits."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current.strip():
                chunks.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


def send_text(to: str, text: str) -> None:
    """Send a plain text message (auto-splits if too long)."""
    for chunk in _split_message(text):
        _send({
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": chunk},
        })


def send_image(to: str, image_url: str, caption: str = "") -> None:
    """Send an image message by URL."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"link": image_url},
    }
    if caption:
        payload["image"]["caption"] = caption[:1024]
    _send(payload)


def send_buttons(to: str, body_text: str, buttons: list[dict]) -> None:
    """
    Send an interactive reply-buttons message.

    buttons: [{"id": "opt_1", "title": "Movie Name"}]
    Max 3 buttons, title max 20 chars.
    """
    _send({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn["id"],
                            "title": btn["title"][:WHATSAPP_MAX_BUTTON_TITLE],
                        },
                    }
                    for btn in buttons[:WHATSAPP_MAX_BUTTONS]
                ]
            },
        },
    })


def send_list(to: str, body_text: str, button_text: str, items: list[dict]) -> None:
    """
    Send an interactive list message (for more than 3 options).

    items: [{"id": "opt_1", "title": "Movie Name", "description": "Year, genre"}]
    Max 10 items.
    """
    _send({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": [
                    {
                        "title": "אפשרויות",
                        "rows": [
                            {
                                "id": item["id"],
                                "title": item["title"][:24],
                                "description": item.get("description", "")[:72],
                            }
                            for item in items[:WHATSAPP_MAX_LIST_ITEMS]
                        ],
                    }
                ],
            },
        },
    })
