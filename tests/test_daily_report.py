import json
from datetime import UTC, datetime
from pathlib import Path

from aws_telegram_daily_brief.models import (
    AwsDailyReport,
    DailyReportSummary,
    ResourceSummary,
    ServiceReport,
)


def test_daily_report_serializes_to_json() -> None:
    report = AwsDailyReport(
        generated_at=datetime(2026, 8, 25, 7, tzinfo=UTC),
        regions=("eu-west-1",),
        summary=DailyReportSummary(1, 1, 0, 0),
        services=(
            ServiceReport(
                service="lambda",
                status="checked",
                resources=(
                    ResourceSummary(
                        service="lambda",
                        resource_type="function",
                        name="demo-daily-brief",
                        region="eu-west-1",
                        state="Active",
                    ),
                ),
            ),
        ),
    )
    serialized = report.to_dict()
    assert serialized["generated_at"] == "2026-08-25T07:00:00+00:00"
    assert json.loads(json.dumps(serialized))["regions"] == ["eu-west-1"]


def test_synthetic_fixture_is_valid_json() -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample_daily_report.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert data["summary"]["resources_detected"] == 3
    assert data["regions"] == ["eu-west-1"]
