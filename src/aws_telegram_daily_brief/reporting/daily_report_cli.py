"""Explicit local AWS report runner; it never sends Telegram."""

from __future__ import annotations

import json

from aws_telegram_daily_brief.aws.client_factory import AwsClientFactory
from aws_telegram_daily_brief.aws.collectors import Ec2Collector, LambdaCollector, SkippedCollector
from aws_telegram_daily_brief.aws.guard import AutomaticSafetyGuard
from aws_telegram_daily_brief.config import Settings
from aws_telegram_daily_brief.reporting.builder import DailyReportBuilder


def main() -> None:
    """Run the registered, free-only collectors and print sanitized JSON."""
    settings = Settings.from_environment()
    factory = AwsClientFactory(settings.aws_region)
    guard = AutomaticSafetyGuard()
    reports = (
        LambdaCollector(factory.create("lambda"), settings.aws_region, guard).collect(),
        Ec2Collector(factory.create("ec2"), settings.aws_region, guard).collect(),
        SkippedCollector("s3", "ListBuckets").collect(),
        SkippedCollector("cloudformation", "DescribeStacks").collect(),
    )
    print(json.dumps(DailyReportBuilder(settings.aws_region).build(reports).to_dict(), indent=2))
