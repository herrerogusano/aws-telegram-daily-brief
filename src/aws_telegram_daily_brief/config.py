"""Strict environment configuration. Secret values are never runtime environment values."""

from __future__ import annotations

import os
from dataclasses import dataclass

from aws_telegram_daily_brief.errors import ConfigurationError

MAX_BEDROCK_OUTPUT_TOKENS = 250
MAX_BEDROCK_INVOCATIONS_PER_RUN = 1
MAX_TELEGRAM_MESSAGES_PER_RUN = 1
MAX_TELEGRAM_TIMEOUT_SECONDS = 30.0
DEFAULT_TELEGRAM_TIMEOUT_SECONDS = 10.0
BEDROCK_MODEL_ID = "amazon.nova-micro-v1:0"


def _flag(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default).lower()).strip().lower()
    if value not in {"true", "false"}:
        raise ConfigurationError(f"{name} must be true or false")
    return value == "true"


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name} is missing or invalid")
    return value


def _positive_float(name: str, default: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)).strip())
    except ValueError:
        raise ConfigurationError(f"{name} is missing or invalid") from None
    if not 0 < value <= maximum:
        raise ConfigurationError(f"{name} is missing or invalid")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    aws_region: str
    report_timezone: str
    log_level: str
    telegram_enabled: bool
    telegram_config_parameter_name: str | None
    telegram_timeout_seconds: float

    @classmethod
    def from_environment(cls) -> Settings:
        region = os.getenv("AWS_REPORT_REGION", os.getenv("AWS_REGION", "eu-west-1")).strip()
        timezone = os.getenv("REPORT_TIMEZONE", "Europe/Madrid").strip()
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        enabled = _flag("TELEGRAM_ENABLED", False)
        parameter = os.getenv("TELEGRAM_CONFIG_PARAMETER_NAME", "").strip() or None
        if not region or not timezone or log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ConfigurationError("safe runtime configuration is invalid")
        if enabled and parameter is None:
            raise ConfigurationError("TELEGRAM_CONFIG_PARAMETER_NAME is missing or invalid")
        return cls(
            region,
            timezone,
            log_level,
            enabled,
            parameter,
            _positive_float("TELEGRAM_TIMEOUT_SECONDS", 10, MAX_TELEGRAM_TIMEOUT_SECONDS),
        )


@dataclass(frozen=True, slots=True)
class TelegramSettings:
    bot_token: str
    chat_id: str
    timeout_seconds: float = DEFAULT_TELEGRAM_TIMEOUT_SECONDS

    @classmethod
    def from_environment(cls) -> TelegramSettings:
        token = _required("TELEGRAM_BOT_TOKEN")
        chat_id = _required("TELEGRAM_CHAT_ID")
        if not _is_valid_chat_id(chat_id):
            raise ConfigurationError("TELEGRAM_CHAT_ID is missing or invalid")
        return cls(token, chat_id, _positive_float("TELEGRAM_TIMEOUT_SECONDS", 10, 30))


def _is_valid_chat_id(chat_id: str) -> bool:
    numeric_value = chat_id[1:] if chat_id.startswith("-") else chat_id
    return bool(numeric_value) and numeric_value.isdecimal() and int(chat_id) != 0


@dataclass(frozen=True, slots=True)
class BedrockSettings:
    enabled: bool = False
    model_id: str = BEDROCK_MODEL_ID
    region: str = "eu-west-1"
    max_output_tokens: int = MAX_BEDROCK_OUTPUT_TOKENS
    temperature: float = 0.1
    timeout_seconds: float = 15.0

    @classmethod
    def from_environment(cls) -> BedrockSettings:
        enabled = _flag("BEDROCK_ENABLED", False)
        model_id = os.getenv("BEDROCK_MODEL_ID", BEDROCK_MODEL_ID).strip()
        region = os.getenv("BEDROCK_REGION", "eu-west-1").strip()
        try:
            max_tokens = int(os.getenv("BEDROCK_MAX_OUTPUT_TOKENS", "250"))
            temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0.1"))
        except ValueError:
            raise ConfigurationError("Bedrock configuration is invalid") from None
        timeout = _positive_float("BEDROCK_TIMEOUT_SECONDS", 15, 30)
        if (
            not model_id
            or model_id != BEDROCK_MODEL_ID
            or not region
            or not 1 <= max_tokens <= MAX_BEDROCK_OUTPUT_TOKENS
            or not 0 <= temperature <= 1
        ):
            raise ConfigurationError("Bedrock configuration is invalid")
        return cls(enabled, model_id, region, max_tokens, temperature, timeout)
