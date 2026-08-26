import logging
from pathlib import Path

import httpx
import pytest

from aws_telegram_daily_brief.aws.guard import AutomaticSafetyGuard, OperationBlockedError
from aws_telegram_daily_brief.aws.operations import OPERATIONS, operation_for
from aws_telegram_daily_brief.config import BedrockSettings, TelegramSettings
from aws_telegram_daily_brief.errors import ConfigurationError, TelegramNotificationError
from aws_telegram_daily_brief.llm.summarizer import BedrockSummarizer
from aws_telegram_daily_brief.models.aws_report import AwsDailyReport
from aws_telegram_daily_brief.notifications.config_provider import (
    ParameterStoreTelegramConfigProvider,
)
from aws_telegram_daily_brief.notifications.telegram import TelegramNotifier


class SecretClient:
    def __init__(self, value: str) -> None:
        self.value, self.calls = value, 0

    def get_parameter(self, **_: object) -> dict[str, object]:
        self.calls += 1
        return {"Parameter": {"Value": self.value}}


class BedrockClient:
    def __init__(self) -> None:
        self.calls = 0

    def converse(self, **_: object) -> dict[str, object]:
        self.calls += 1
        return {"output": {"message": {"content": [{"text": "ok"}]}}}


class HttpClient:
    def post(self, url: str, *, json: dict[str, str], timeout: float) -> httpx.Response:
        del url, json, timeout
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})


def test_registry_classifies_each_runtime_operation_once() -> None:
    classifications = {
        "free_verified_read",
        "controlled_billable",
        "operational_secret_read",
        "write",
        "sensitive_read",
        "unknown",
    }
    assert len({(item.service, item.operation) for item in OPERATIONS}) == len(OPERATIONS)
    assert {item.classification for item in OPERATIONS} <= classifications
    assert not [item for item in OPERATIONS if item.classification == "write" and item.required]


def test_guard_blocks_unknown_sensitive_and_write_operations() -> None:
    guard = AutomaticSafetyGuard()
    for operation in (
        operation_for("s3", "ListBuckets"),
        operation_for("cloudformation", "DescribeStacks"),
    ):
        with pytest.raises(OperationBlockedError):
            guard.execute(object(), operation)


def test_parameter_store_is_guarded_cached_and_sanitized(caplog: pytest.LogCaptureFixture) -> None:
    token, chat_id = "secret-token", "987654"
    client = SecretClient(f'{{"bot_token":"{token}","chat_id":"{chat_id}"}}')
    provider = ParameterStoreTelegramConfigProvider(
        client, "/telegram-daily-brief/telegram/config", AutomaticSafetyGuard()
    )
    with caplog.at_level(logging.INFO):
        assert provider.get_config().bot_token == token
        assert provider.get_config().chat_id == chat_id
    assert client.calls == 1
    assert token not in caplog.text and chat_id not in caplog.text
    with pytest.raises(ConfigurationError, match="unavailable"):
        ParameterStoreTelegramConfigProvider(object(), "/safe", AutomaticSafetyGuard()).get_config()


def test_bedrock_can_only_call_once_when_explicitly_enabled() -> None:
    client = BedrockClient()
    summarizer = BedrockSummarizer(BedrockSettings(enabled=True), client)
    assert summarizer.summarize(AwsDailyReport.empty("eu-west-1")).generated_by == "bedrock"
    with pytest.raises(Exception, match="invocation_limit"):
        summarizer.summarize(AwsDailyReport.empty("eu-west-1"))
    assert client.calls == 1


def test_telegram_never_sends_more_than_one_message() -> None:
    notifier = TelegramNotifier(TelegramSettings("safe-token", "123456"), HttpClient())
    notifier.send_message("one")
    with pytest.raises(TelegramNotificationError, match="message_limit"):
        notifier.send_message("two")


def test_template_is_restrictive_and_has_one_schedule() -> None:
    template = Path("template.yaml").read_text(encoding="utf-8")
    expected_actions = {
        item.iam_action
        for item in OPERATIONS
        if item.required or item.classification == "controlled_billable"
    }
    for action in expected_actions:
        assert action in template
    forbidden = (
        'Action: "*"',
        "ec2:*",
        "iam:*",
        "kms:*",
        "ssm:PutParameter",
        "secretsmanager:GetSecretValue",
        "ce:GetCostAndUsage",
        "ProvisionedConcurrencyConfig",
    )
    assert not any(value in template for value in forbidden)
    assert template.count("Type: ScheduleV2") == 1
    assert "MaximumRetryAttempts: 0" in template
    assert "FunctionName: aws-telegram-daily-brief" in template
    assert "LogGroupName: /aws/lambda/aws-telegram-daily-brief" in template
    assert "RetentionInDays: 14" in template


def test_malicious_event_cannot_raise_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BEDROCK_ENABLED", "true")
    monkeypatch.setenv("BEDROCK_MAX_OUTPUT_TOKENS", "99999")
    with pytest.raises(ConfigurationError):
        BedrockSettings.from_environment()
