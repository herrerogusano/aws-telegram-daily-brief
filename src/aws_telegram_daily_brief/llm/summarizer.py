"""Protocol for the future optional Bedrock summary implementation."""

from typing import Protocol

from aws_telegram_daily_brief.models import DailyAwsReport


class ReportSummarizer(Protocol):
    """Render a report to a concise human-readable message."""

    def summarize(self, report: DailyAwsReport) -> str:
        """Return a message or raise BedrockSummaryError for fallback handling."""
