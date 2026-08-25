"""Read-only scheduled Lambda entry point with bounded external side effects."""

from __future__ import annotations

import logging
from typing import Any

from aws_telegram_daily_brief.aws.client_factory import AwsClientFactory
from aws_telegram_daily_brief.aws.collectors import Ec2Collector, LambdaCollector, SkippedCollector
from aws_telegram_daily_brief.aws.guard import AutomaticSafetyGuard
from aws_telegram_daily_brief.config import BedrockSettings, Settings, TelegramSettings
from aws_telegram_daily_brief.errors import ConfigurationError, TelegramNotificationError
from aws_telegram_daily_brief.llm.summarizer import (
    BedrockSummarizer,
    DeterministicSummarizer,
    FallbackSummarizer,
)
from aws_telegram_daily_brief.notifications.config_provider import (
    ParameterStoreTelegramConfigProvider,
)
from aws_telegram_daily_brief.notifications.policy import should_notify
from aws_telegram_daily_brief.notifications.telegram import TelegramNotifier
from aws_telegram_daily_brief.reporting.builder import DailyReportBuilder

logger = logging.getLogger(__name__)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Generate one report. Event data cannot add operations, calls, or permissions."""
    settings = Settings.from_environment()
    factory = AwsClientFactory(settings.aws_region)
    guard = AutomaticSafetyGuard()
    reports = (
        LambdaCollector(factory.create("lambda"), settings.aws_region, guard).collect(),
        Ec2Collector(factory.create("ec2"), settings.aws_region, guard).collect(),
        SkippedCollector("s3", "ListBuckets").collect(),
        SkippedCollector("cloudformation", "DescribeStacks").collect(),
    )
    report = DailyReportBuilder(settings.aws_region).build(reports)
    brief = _summarize(report, factory, guard)
    status = "partial" if report.summary.warnings else "ok"
    notification = {"attempted": False, "success": False}
    if should_notify(event, settings.telegram_enabled):
        notification, failed = _notify(brief.text, factory, settings, guard)
        if failed:
            status = "partial"
    return {
        "status": status,
        "report": report.to_dict()["summary"],
        "brief": {
            "generated_by": brief.generated_by,
            "fallback_used": brief.fallback_used,
            "text": brief.text,
        },
        "notification": notification,
    }


def _summarize(report: Any, factory: AwsClientFactory, guard: AutomaticSafetyGuard) -> Any:
    settings = BedrockSettings.from_environment()
    if not settings.enabled:
        return DeterministicSummarizer().summarize(report)
    primary = BedrockSummarizer(
        settings,
        factory.create_bedrock_runtime(timeout_seconds=settings.timeout_seconds),
        guard=guard,
    )
    return FallbackSummarizer(primary, DeterministicSummarizer()).summarize(report)


def _notify(
    text: str, factory: AwsClientFactory, settings: Settings, guard: AutomaticSafetyGuard
) -> tuple[dict[str, bool], bool]:
    assert settings.telegram_config_parameter_name is not None
    try:
        config = ParameterStoreTelegramConfigProvider(
            factory.create("ssm"), settings.telegram_config_parameter_name, guard
        ).get_config()
        notifier = TelegramNotifier(
            TelegramSettings(config.bot_token, config.chat_id, settings.telegram_timeout_seconds)
        )
        try:
            notifier.send_message(text)
        finally:
            notifier.close()
        return {"attempted": True, "success": True}, False
    except (ConfigurationError, TelegramNotificationError):
        logger.warning("telegram_notification_unavailable")
        return {"attempted": False, "success": False}, True
