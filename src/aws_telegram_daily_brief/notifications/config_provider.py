"""Load Telegram configuration from one decrypted Parameter Store value."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from aws_telegram_daily_brief.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


class ParameterStoreTelegramConfigProvider:
    def __init__(self, client: Any, parameter_name: str) -> None:
        self.client, self.parameter_name = client, parameter_name
        self._cached: TelegramConfig | None = None

    def get_config(self) -> TelegramConfig:
        if self._cached is not None:
            return self._cached
        try:
            value = self.client.get_parameter(Name=self.parameter_name, WithDecryption=True)[
                "Parameter"
            ]["Value"]
        except (ClientError, BotoCoreError, KeyError, TypeError):
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
