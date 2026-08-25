"""Protocol for the future Telegram implementation."""

from typing import Protocol


class TelegramNotifier(Protocol):
    """Send pre-rendered text without exposing token handling to callers."""

    def send_message(self, text: str) -> None:
        """Deliver one text message to the configured chat."""
