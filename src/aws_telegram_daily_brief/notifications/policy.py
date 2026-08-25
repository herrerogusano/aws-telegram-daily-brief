"""Explicitly prevent accidental manual Telegram delivery."""

from typing import Any


def should_notify(event: dict[str, Any], enabled: bool) -> bool:
    return enabled and (
        event.get("source") == "eventbridge-scheduler"
        or (event.get("source") == "manual-test" and event.get("send_notification") is True)
    )
