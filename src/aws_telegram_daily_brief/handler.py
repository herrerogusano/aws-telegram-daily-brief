"""Read-only daily Lambda with partial success, time budgets and safe observability."""

from __future__ import annotations

from time import perf_counter
from typing import Any
from uuid import uuid4

from aws_telegram_daily_brief.aws.client_factory import AwsClientFactory
from aws_telegram_daily_brief.aws.collectors import Ec2Collector, LambdaCollector, SkippedCollector
from aws_telegram_daily_brief.aws.guard import AutomaticSafetyGuard
from aws_telegram_daily_brief.config import BedrockSettings, Settings, TelegramSettings
from aws_telegram_daily_brief.errors import (
    BedrockSummaryError,
    ConfigurationError,
    TelegramNotificationError,
)
from aws_telegram_daily_brief.execution import (
    ErrorComponent,
    ExecutionError,
    ExecutionResult,
    madrid_report_date,
)
from aws_telegram_daily_brief.llm.summarizer import BedrockSummarizer, DeterministicSummarizer
from aws_telegram_daily_brief.notifications.config_provider import (
    ParameterStoreTelegramConfigProvider,
)
from aws_telegram_daily_brief.notifications.policy import should_notify
from aws_telegram_daily_brief.notifications.telegram import TelegramNotifier
from aws_telegram_daily_brief.observability import log_event
from aws_telegram_daily_brief.reporting.builder import DailyReportBuilder

BEDROCK_MIN_REMAINING_MS = 20_000
CLEANUP_MARGIN_MS = 2_000


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Create one brief; untrusted event data cannot raise side-effect limits."""
    started = perf_counter()
    execution = ExecutionResult(str(uuid4()), madrid_report_date(), _trigger_type(event))
    log_event(
        "execution_started",
        execution.execution_id,
        execution.report_date,
        trigger_type=execution.trigger_type,
    )
    try:
        settings = Settings.from_environment()
        factory, guard = AwsClientFactory(settings.aws_region), AutomaticSafetyGuard()
        reports = _collect(factory, settings, guard, execution)
        report = DailyReportBuilder(settings.aws_region).build(reports)
        execution.report_status = "partial" if report.summary.warnings else "complete"
        execution.metrics.update(
            {
                "resources_detected": report.summary.resources_detected,
                "services_checked": report.summary.services_checked,
                "services_failed": sum(
                    service.status in {"error", "timeout", "permission_denied", "unavailable"}
                    for service in reports
                ),
            }
        )
        log_event(
            "report_built",
            execution.execution_id,
            execution.report_date,
            status=execution.report_status,
        )
        brief = _summarize(report, factory, guard, execution, context)
        execution.summary_source = brief.generated_by
        if should_notify(event, settings.telegram_enabled):
            _notify(brief.text, factory, settings, guard, execution, context)
        execution.metrics["total_duration_ms"] = int((perf_counter() - started) * 1000)
        log_event(
            "execution_completed",
            execution.execution_id,
            execution.report_date,
            status=execution.status,
            **execution.metrics,
        )
        return execution.response(report.to_dict()["summary"])
    except ConfigurationError:
        execution.status = execution.status.FAILED
        execution.errors.append(
            ExecutionError(
                "invalid_configuration",
                ErrorComponent.CONFIGURATION,
                False,
                "configuration unavailable",
            )
        )
    except Exception:
        execution.status = execution.status.FAILED
        execution.errors.append(
            ExecutionError("internal_failure", ErrorComponent.INTERNAL, False, "internal failure")
        )
    execution.metrics["total_duration_ms"] = int((perf_counter() - started) * 1000)
    log_event(
        "execution_failed", execution.execution_id, execution.report_date, status=execution.status
    )
    return execution.response({})


def _collect(
    factory: AwsClientFactory,
    settings: Settings,
    guard: AutomaticSafetyGuard,
    execution: ExecutionResult,
) -> tuple[Any, ...]:
    collectors = (
        ("lambda", LambdaCollector(factory.create("lambda"), settings.aws_region, guard)),
        ("ec2", Ec2Collector(factory.create("ec2"), settings.aws_region, guard)),
        ("s3", SkippedCollector("s3", "ListBuckets")),
        ("cloudformation", SkippedCollector("cloudformation", "DescribeStacks")),
    )
    reports = []
    for name, collector in collectors:
        log_event(
            "collector_started", execution.execution_id, execution.report_date, component=name
        )
        report = collector.collect()
        reports.append(report)
        event = (
            "collector_skipped" if report.status.startswith("skipped_") else "collector_completed"
        )
        if report.status in {"error", "timeout", "permission_denied", "unavailable"}:
            event = "collector_failed"
            execution.partial(
                ExecutionError(
                    "collection_failed",
                    ErrorComponent.AWS_COLLECTION,
                    True,
                    "collector unavailable",
                )
            )
        log_event(
            event,
            execution.execution_id,
            execution.report_date,
            component=name,
            status=report.status,
        )
    return tuple(reports)


def _summarize(
    report: Any,
    factory: AwsClientFactory,
    guard: AutomaticSafetyGuard,
    execution: ExecutionResult,
    context: Any,
) -> Any:
    settings = BedrockSettings.from_environment()
    if not settings.enabled:
        return DeterministicSummarizer().summarize(report)
    if _remaining_ms(context) < BEDROCK_MIN_REMAINING_MS:
        execution.warnings.append("bedrock_skipped_due_to_time_budget")
        log_event(
            "deterministic_fallback_used",
            execution.execution_id,
            execution.report_date,
            component="bedrock",
            status="time_budget",
        )
        return DeterministicSummarizer().summarize(report)
    log_event("bedrock_invocation_started", execution.execution_id, execution.report_date)
    try:
        brief = BedrockSummarizer(
            settings,
            factory.create_bedrock_runtime(timeout_seconds=settings.timeout_seconds),
            guard=guard,
        ).summarize(report)
        execution.metrics["bedrock_invocations"] = 1
        log_event("bedrock_invocation_completed", execution.execution_id, execution.report_date)
        return brief
    except BedrockSummaryError:
        execution.warnings.append("bedrock_fallback")
        log_event("bedrock_invocation_failed", execution.execution_id, execution.report_date)
        log_event(
            "deterministic_fallback_used",
            execution.execution_id,
            execution.report_date,
            component="bedrock",
        )
        return DeterministicSummarizer().summarize(report)


def _notify(
    text: str,
    factory: AwsClientFactory,
    settings: Settings,
    guard: AutomaticSafetyGuard,
    execution: ExecutionResult,
    context: Any,
) -> None:
    if _remaining_ms(context) < int(settings.telegram_timeout_seconds * 1000) + CLEANUP_MARGIN_MS:
        execution.notification_status = "skipped_due_to_time_budget"
        execution.partial(
            ExecutionError(
                "notification_time_budget",
                ErrorComponent.TIME_BUDGET,
                False,
                "notification skipped",
            )
        )
        return
    execution.notification_status = "attempted"
    log_event("notification_started", execution.execution_id, execution.report_date)
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
        execution.notification_status = "sent"
        log_event(
            "notification_completed", execution.execution_id, execution.report_date, status="sent"
        )
    except ConfigurationError:
        execution.notification_status = "configuration_failed"
        execution.partial(
            ExecutionError(
                "secret_unavailable",
                ErrorComponent.SECRET_PROVIDER,
                False,
                "configuration unavailable",
            )
        )
        log_event(
            "notification_failed",
            execution.execution_id,
            execution.report_date,
            component="secret_provider",
        )
    except TelegramNotificationError:
        execution.notification_status = "failed"
        execution.partial(
            ExecutionError(
                "telegram_failed", ErrorComponent.TELEGRAM, True, "notification unavailable"
            )
        )
        log_event(
            "notification_failed",
            execution.execution_id,
            execution.report_date,
            component="telegram",
        )


def _remaining_ms(context: Any) -> int:
    callback = getattr(context, "get_remaining_time_in_millis", None)
    return int(callback()) if callable(callback) else 60_000


def _trigger_type(event: dict[str, Any]) -> str:
    return "scheduled" if event.get("source") == "eventbridge-scheduler" else "manual"
