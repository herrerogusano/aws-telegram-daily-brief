"""Load Telegram configuration from one decrypted Parameter Store value."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from aws_telegram_daily_brief.aws.guard import AutomaticSafetyGuard
from aws_telegram_daily_brief.aws.operations import operation_for
from aws_telegram_daily_brief.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


class ParameterStoreTelegramConfigProvider:
    def __init__(self, client: Any, parameter_name: str, guard: AutomaticSafetyGuard) -> None:
        self.client, self.parameter_name, self.guard = client, parameter_name, guard
        self._cached: TelegramConfig | None = None

    def get_config(self) -> TelegramConfig:
        if self._cached is not None:
            return self._cached
        try:
            value = self.guard.execute_secret_read(
                self.client,
                operation_for("ssm", "GetParameter"),
                Name=self.parameter_name,
                WithDecryption=True,
            )["Parameter"]["Value"]
        except (ClientError, BotoCoreError, KeyError, TypeError, ValueError):
            raise ConfigurationError("Telegram configuration is unavailable") from None
        try:
            data = json.loads(value)
            config = TelegramConfig(str(data["bot_token"]), str(data["chat_id"]))
        except (ValueError, KeyError, TypeError):
            raise ConfigurationError("Telegram configuration is invalid") from None
        if not config.bot_token or not config.chat_id:
            raise ConfigurationError("Telegram configuration is invalid")
        self._cached = config
        return config
