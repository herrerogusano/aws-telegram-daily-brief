import json
from datetime import UTC, datetime
from pathlib import Path

from aws_telegram_daily_brief.models import DailyAwsReport


def test_daily_report_serializes_to_json() -> None:
    report = DailyAwsReport(
        generated_at=datetime(2026, 8, 25, 7, tzinfo=UTC),
        region_scope=("eu-west-1",),
        warnings=("Synthetic warning",),
    )
    serialized = report.to_dict()
    assert serialized["generated_at"] == "2026-08-25T07:00:00+00:00"
    assert json.loads(json.dumps(serialized))["region_scope"] == ["eu-west-1"]


def test_synthetic_fixture_is_valid_json() -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample_daily_report.json"
    assert json.loads(fixture.read_text(encoding="utf-8"))["inventory"]["total_resources"] == 3
