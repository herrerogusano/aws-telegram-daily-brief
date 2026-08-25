"""Environment-backed configuration without secret resolution."""

from __future__ import annotations

import os
from dataclasses import dataclass

from aws_telegram_daily_brief.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Settings:
    """Safe runtime settings; secret values are intentionally not loaded here."""

    aws_region: str = "eu-west-1"
    report_timezone: str = "Europe/Madrid"
    log_level: str = "INFO"
    telegram_chat_id: str | None = None
    telegram_bot_token_secret_name: str | None = None
    bedrock_model_id: str | None = None

    @classmethod
    def from_environment(cls) -> Settings:
        region = os.getenv("AWS_REGION", "eu-west-1").strip()
        timezone = os.getenv("REPORT_TIMEZONE", "Europe/Madrid").strip()
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        if not region:
            raise ConfigurationError("AWS_REGION must not be empty")
        if not timezone:
            raise ConfigurationError("REPORT_TIMEZONE must not be empty")
        return cls(
            aws_region=region,
            report_timezone=timezone,
            log_level=log_level,
            telegram_chat_id=_optional_environment_value("TELEGRAM_CHAT_ID"),
            telegram_bot_token_secret_name=_optional_environment_value(
                "TELEGRAM_BOT_TOKEN_SECRET_NAME"
            ),
            bedrock_model_id=_optional_environment_value("BEDROCK_MODEL_ID"),
        )


def _optional_environment_value(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


@dataclass(frozen=True, slots=True)
class TelegramSettings:
    """Local Telegram settings, loaded only by the explicit test entry point."""

    bot_token: str
    chat_id: str
    timeout_seconds: float = 10.0

    @classmethod
    def from_environment(cls) -> TelegramSettings:
        token = _required_environment_value("TELEGRAM_BOT_TOKEN")
        chat_id = _required_environment_value("TELEGRAM_CHAT_ID")
        if not _is_valid_chat_id(chat_id):
            raise ConfigurationError("TELEGRAM_CHAT_ID is missing or invalid")
        timeout = _telegram_timeout_from_environment()
        return cls(bot_token=token, chat_id=chat_id, timeout_seconds=timeout)


def _required_environment_value(name: str) -> str:
    value = _optional_environment_value(name)
    if value is None:
        raise ConfigurationError(f"{name} is missing or invalid")
    return value


def _is_valid_chat_id(chat_id: str) -> bool:
    numeric_value = chat_id[1:] if chat_id.startswith("-") else chat_id
    return bool(numeric_value) and numeric_value.isdecimal() and int(chat_id) != 0


def _telegram_timeout_from_environment() -> float:
    raw_timeout = os.getenv("TELEGRAM_TIMEOUT_SECONDS", "10").strip()
    try:
        timeout = float(raw_timeout)
    except ValueError as error:
        raise ConfigurationError("TELEGRAM_TIMEOUT_SECONDS is missing or invalid") from error
    if not 0 < timeout <= 60:
        raise ConfigurationError("TELEGRAM_TIMEOUT_SECONDS is missing or invalid")
    return timeout
