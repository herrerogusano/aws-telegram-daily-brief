from pathlib import Path


def test_schedule_is_disabled_and_uses_madrid_timezone() -> None:
    template = Path("template.yaml").read_text(encoding="utf-8")
    assert "Type: ScheduleV2" in template
    assert "cron(0 9 * * ? *)" in template
    assert "ScheduleExpressionTimezone: Europe/Madrid" in template
    assert "State: DISABLED" in template
    assert "MaximumRetryAttempts: 0" in template
    assert template.count("Type: ScheduleV2") == 1
