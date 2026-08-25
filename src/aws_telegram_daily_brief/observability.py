"""Sanitized structured logging; never accepts raw external payloads."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_event(event: str, execution_id: str, report_date: str, **fields: Any) -> None:
    safe = {
        key: value
        for key, value in fields.items()
        if key not in {"text", "token", "chat_id", "url", "prompt"}
    }
    logger.info(
        event,
        extra={"event": event, "execution_id": execution_id, "report_date": report_date, **safe},
    )
