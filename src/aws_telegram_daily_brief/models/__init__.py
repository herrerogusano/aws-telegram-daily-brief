"""Serializable, SDK-independent domain models."""

from aws_telegram_daily_brief.models.aws_report import (
    AwsDailyReport,
    DailyReportSummary,
    ResourceSummary,
    ServiceReport,
)

__all__ = ["AwsDailyReport", "DailyReportSummary", "ResourceSummary", "ServiceReport"]
