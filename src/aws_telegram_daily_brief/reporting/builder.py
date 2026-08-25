"""Build one valid report even when individual services are partial."""

from datetime import UTC, datetime

from aws_telegram_daily_brief.models.aws_report import (
    AwsDailyReport,
    DailyReportSummary,
    ServiceReport,
)


class DailyReportBuilder:
    def __init__(self, region: str) -> None:
        self.region = region

    def build(self, reports: tuple[ServiceReport, ...]) -> AwsDailyReport:
        checked = sum(report.status in {"checked", "empty"} for report in reports)
        skipped = sum(report.status.startswith("skipped_") for report in reports)
        warnings = sum(report.status not in {"checked", "empty"} for report in reports)
        return AwsDailyReport(
            datetime.now(UTC),
            (self.region,),
            DailyReportSummary(
                sum(len(report.resources) for report in reports), checked, skipped, warnings
            ),
            reports,
        )
