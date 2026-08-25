import logging

import httpx
import pytest

from aws_telegram_daily_brief.config import TelegramSettings
from aws_telegram_daily_brief.errors import TelegramNotificationError
from aws_telegram_daily_brief.notifications.telegram import (
    MAX_TELEGRAM_MESSAGE_LENGTH,
    TelegramNotifier,
)

TOKEN = "test-token-that-must-not-appear-in-logs"


class FakeHttpClient:
    def __init__(self, result: httpx.Response | Exception) -> None:
        self.result = result
        self.url: str | None = None
        self.json: dict[str, str] | None = None
        self.timeout: float | None = None

    def post(self, url: str, *, json: dict[str, str], timeout: float) -> httpx.Response:
        self.url = url
        self.json = json
        self.timeout = timeout
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _settings() -> TelegramSettings:
    return TelegramSettings(bot_token=TOKEN, chat_id="123456", timeout_seconds=7.5)


def _notifier(result: httpx.Response | Exception) -> tuple[TelegramNotifier, FakeHttpClient]:
    client = FakeHttpClient(result)
    return TelegramNotifier(_settings(), client), client


def test_send_message_returns_normalized_success() -> None:
    notifier, client = _notifier(
        httpx.Response(200, json={"ok": True, "result": {"message_id": 123}})
    )
    result = notifier.send_message("Hello")
    assert result.success is True
    assert result.message_id == 123
    assert result.status_code == 200
    assert client.json == {"chat_id": "123456", "text": "Hello"}
    assert client.timeout == 7.5


@pytest.mark.parametrize("status_code", [400, 401, 403, 429, 500])
def test_send_message_rejects_telegram_http_errors(status_code: int) -> None:
    notifier, _ = _notifier(
        httpx.Response(status_code, json={"ok": False, "description": "ignored"})
    )
    with pytest.raises(TelegramNotificationError) as error:
        notifier.send_message("Hello")
    assert error.value.error_kind == "telegram_api_error"
    assert error.value.status_code == status_code


def test_send_message_rejects_ok_false_even_with_http_200() -> None:
    notifier, _ = _notifier(httpx.Response(200, json={"ok": False}))
    with pytest.raises(TelegramNotificationError, match="telegram_api_error"):
        notifier.send_message("Hello")


def test_send_message_rejects_invalid_json() -> None:
    notifier, _ = _notifier(httpx.Response(200, content=b"not json"))
    with pytest.raises(TelegramNotificationError, match="invalid_response"):
        notifier.send_message("Hello")


def test_send_message_rejects_missing_message_id() -> None:
    notifier, _ = _notifier(httpx.Response(200, json={"ok": True, "result": {}}))
    with pytest.raises(TelegramNotificationError, match="invalid_response"):
        notifier.send_message("Hello")


def test_send_message_translates_timeout() -> None:
    request = httpx.Request("POST", "https://api.telegram.org/placeholder")
    notifier, _ = _notifier(httpx.TimeoutException("timeout", request=request))
    with pytest.raises(TelegramNotificationError, match="timeout"):
        notifier.send_message("Hello")


def test_send_message_translates_network_error() -> None:
    request = httpx.Request("POST", "https://api.telegram.org/placeholder")
    notifier, _ = _notifier(httpx.NetworkError("offline", request=request))
    with pytest.raises(TelegramNotificationError, match="network_error"):
        notifier.send_message("Hello")


def test_send_message_rejects_messages_over_telegram_limit() -> None:
    notifier, client = _notifier(
        httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    )
    with pytest.raises(TelegramNotificationError, match="message_too_long"):
        notifier.send_message("x" * (MAX_TELEGRAM_MESSAGE_LENGTH + 1))
    assert client.url is None


def test_logs_and_errors_do_not_expose_token(caplog: pytest.LogCaptureFixture) -> None:
    request = httpx.Request("POST", f"https://api.telegram.org/bot{TOKEN}/sendMessage")
    notifier, _ = _notifier(httpx.NetworkError(f"failed {request.url}", request=request))
    with caplog.at_level(logging.INFO):
        with pytest.raises(TelegramNotificationError) as error:
            notifier.send_message("Sensitive report content")
    assert TOKEN not in str(error.value)
    assert TOKEN not in caplog.text
    assert "Sensitive report content" not in caplog.text
    assert "https://api.telegram.org/bot" not in caplog.text
