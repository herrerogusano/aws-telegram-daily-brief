import pytest

from aws_telegram_daily_brief.config import Settings
from aws_telegram_daily_brief.errors import ConfigurationError


def test_settings_have_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("REPORT_TIMEZONE", raising=False)
    settings = Settings.from_environment()
    assert settings.aws_region == "eu-west-1"
    assert settings.report_timezone == "Europe/Madrid"


def test_empty_region_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_REGION", "  ")
    with pytest.raises(ConfigurationError):
        Settings.from_environment()
