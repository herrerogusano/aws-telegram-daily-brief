"""A small, outbound-only Telegram Bot API boundary."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from aws_telegram_daily_brief.config import MAX_TELEGRAM_MESSAGES_PER_RUN, TelegramSettings
from aws_telegram_daily_brief.errors import TelegramNotificationError

MAX_TELEGRAM_MESSAGE_LENGTH = 4096
logger = logging.getLogger(__name__)


class HttpClient(Protocol):
    """The limited HTTP surface needed by this notifier."""

    def post(self, url: str, *, json: dict[str, str], timeout: float) -> httpx.Response: ...


@dataclass(frozen=True, slots=True)
class TelegramSendResult:
    """The safe subset of a successful Telegram send response."""

    success: bool
    message_id: int
    status_code: int


class TelegramNotifier:
    """Send plain-text messages without exposing Telegram API details to callers."""

    def __init__(self, settings: TelegramSettings, client: HttpClient | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(follow_redirects=False, trust_env=False)
        self._owns_client = client is None
        self._messages_sent = 0

    def close(self) -> None:
        """Close the internally created HTTP client, if any."""
        if self._owns_client:
            assert isinstance(self._client, httpx.Client)
            self._client.close()

    def send_message(self, text: str) -> TelegramSendResult:
        """Send one message once, with an explicit timeout and sanitized failures."""
        if not text:
            raise TelegramNotificationError("invalid_message")
        if len(text) > MAX_TELEGRAM_MESSAGE_LENGTH:
            raise TelegramNotificationError("message_too_long")
        if self._messages_sent >= MAX_TELEGRAM_MESSAGES_PER_RUN:
            raise TelegramNotificationError("message_limit")

        logger.info("telegram_send_started", extra={"message_length": len(text)})
        try:
            response = self._client.post(
                self._api_url(),
                json={"chat_id": self._settings.chat_id, "text": text},
                timeout=self._settings.timeout_seconds,
            )
        except httpx.TimeoutException:
            self._log_failure("timeout")
            raise TelegramNotificationError("timeout") from None
        except httpx.RequestError:
            self._log_failure("network_error")
            raise TelegramNotificationError("network_error") from None

        payload = self._response_payload(response)
        if not response.is_success or payload.get("ok") is not True:
            self._log_failure("telegram_api_error", response.status_code)
            raise TelegramNotificationError("telegram_api_error", response.status_code)

        result = payload.get("result")
        message_id = result.get("message_id") if isinstance(result, Mapping) else None
        if not isinstance(message_id, int) or isinstance(message_id, bool):
            self._log_failure("invalid_response", response.status_code)
            raise TelegramNotificationError("invalid_response", response.status_code)

        logger.info("telegram_send_succeeded", extra={"status_code": response.status_code})
        self._messages_sent += 1
        return TelegramSendResult(
            success=True, message_id=message_id, status_code=response.status_code
        )

    def _api_url(self) -> str:
        return f"https://api.telegram.org/bot{self._settings.bot_token}/sendMessage"

    def _response_payload(self, response: httpx.Response) -> Mapping[str, Any]:
        try:
            payload = response.json()
        except (ValueError, httpx.DecodingError):
            self._log_failure("invalid_response", response.status_code)
            raise TelegramNotificationError("invalid_response", response.status_code) from None
        if not isinstance(payload, Mapping):
            self._log_failure("invalid_response", response.status_code)
            raise TelegramNotificationError("invalid_response", response.status_code)
        return payload

    @staticmethod
    def _log_failure(error_kind: str, status_code: int | None = None) -> None:
        logger.warning(
            "telegram_send_failed",
            extra={"error_kind": error_kind, "status_code": status_code},
        )
