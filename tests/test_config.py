import pytest

from aws_telegram_daily_brief.config import Settings, TelegramSettings
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


def test_telegram_settings_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-1001234567890")
    settings = TelegramSettings.from_environment()
    assert settings.bot_token == "test-token"
    assert settings.chat_id == "-1001234567890"
    assert settings.timeout_seconds == 10.0


@pytest.mark.parametrize("name", ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"])
def test_telegram_settings_require_credentials(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
    monkeypatch.delenv(name)
    with pytest.raises(ConfigurationError):
        TelegramSettings.from_environment()


@pytest.mark.parametrize("chat_id", ["chat", "0", "-", "12.5"])
def test_telegram_settings_reject_invalid_chat_id(
    monkeypatch: pytest.MonkeyPatch, chat_id: str
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", chat_id)
    with pytest.raises(ConfigurationError, match="TELEGRAM_CHAT_ID is missing or invalid"):
        TelegramSettings.from_environment()


@pytest.mark.parametrize("value", ["0", "61", "not-a-number"])
def test_telegram_settings_reject_invalid_timeout(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
    monkeypatch.setenv("TELEGRAM_TIMEOUT_SECONDS", value)
    with pytest.raises(ConfigurationError, match="TELEGRAM_TIMEOUT_SECONDS is missing or invalid"):
        TelegramSettings.from_environment()
