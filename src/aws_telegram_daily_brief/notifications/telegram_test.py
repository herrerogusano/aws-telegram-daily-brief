"""Explicit manual test entry point for local Telegram delivery."""

from __future__ import annotations

import logging

from aws_telegram_daily_brief.config import TelegramSettings
from aws_telegram_daily_brief.errors import ConfigurationError, TelegramNotificationError
from aws_telegram_daily_brief.notifications.telegram import TelegramNotifier

TEST_MESSAGE = "AWS Telegram Daily Brief ✅\n\nTelegram integration is working."


def main() -> None:
    """Send exactly one controlled message when invoked explicitly by a developer."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    notifier: TelegramNotifier | None = None
    try:
        notifier = TelegramNotifier(TelegramSettings.from_environment())
        result = notifier.send_message(TEST_MESSAGE)
    except (ConfigurationError, TelegramNotificationError) as error:
        print(f"Telegram test failed: {error}")
        raise SystemExit(1) from None
    finally:
        if notifier is not None:
            notifier.close()
    print(f"Telegram test succeeded (status_code={result.status_code}).")
