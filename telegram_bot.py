"""Telegram messaging for the Forex bot."""

from __future__ import annotations

import logging

import requests

from config import TELEGRAM_CHAT_ID, TELEGRAM_TOKEN


logger = logging.getLogger(__name__)


def send_telegram(message: str) -> None:
    """Send message to Telegram; raises on failure."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
        },
        timeout=30,
    )

    logger.info("Telegram Response: status_code=%s", response.status_code)
    logger.debug("Telegram Response body: %s", response.text)

    response.raise_for_status()


