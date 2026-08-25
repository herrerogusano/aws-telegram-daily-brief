"""Lambda entry point for Phase 0."""

from __future__ import annotations

import logging
from typing import Any

from aws_telegram_daily_brief.config import Settings

logger = logging.getLogger(__name__)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, str]:
    """Return a safe bootstrap response without contacting AWS or Telegram."""
    settings = Settings.from_environment()
    logger.info(
        "daily_brief_initialized",
        extra={"region": settings.aws_region, "timezone": settings.report_timezone},
    )
    return {"status": "ok", "message": "AWS Telegram Daily Brief initialized"}
