"""Lambda entry point for Phase 0."""

from __future__ import annotations

import logging
import os
from typing import Any

from aws_telegram_daily_brief.aws.client_factory import AwsClientFactory
from aws_telegram_daily_brief.aws.collectors import Ec2Collector, LambdaCollector, SkippedCollector
from aws_telegram_daily_brief.aws.guard import AutomaticSafetyGuard
from aws_telegram_daily_brief.config import Settings, TelegramSettings
from aws_telegram_daily_brief.llm.summarizer import DeterministicSummarizer
from aws_telegram_daily_brief.notifications.config_provider import (
    ParameterStoreTelegramConfigProvider,
)
from aws_telegram_daily_brief.notifications.policy import should_notify
from aws_telegram_daily_brief.notifications.telegram import TelegramNotifier
from aws_telegram_daily_brief.reporting.builder import DailyReportBuilder

logger = logging.getLogger(__name__)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Build an AWS brief without Telegram or scheduler coupling."""
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
    brief = DeterministicSummarizer().summarize(report)
    status = "partial" if report.summary.warnings else "ok"
    notification = {"attempted": False, "success": False}
    enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
    if should_notify(event, enabled):
        config = ParameterStoreTelegramConfigProvider(
            factory.create("ssm"), os.environ["TELEGRAM_CONFIG_PARAMETER_NAME"]
        ).get_config()
        notifier = TelegramNotifier(TelegramSettings(config.bot_token, config.chat_id))
        try:
            notifier.send_message(brief.text)
            notification = {"attempted": True, "success": True}
        except Exception:
            notification = {"attempted": True, "success": False}
            status = "partial"
        finally:
            notifier.close()
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
