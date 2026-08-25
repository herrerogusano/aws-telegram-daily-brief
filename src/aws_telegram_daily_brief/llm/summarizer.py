"""Bounded Bedrock and deterministic report summarizers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from aws_telegram_daily_brief.aws.guard import AutomaticSafetyGuard
from aws_telegram_daily_brief.aws.operations import operation_for
from aws_telegram_daily_brief.config import BedrockSettings
from aws_telegram_daily_brief.errors import BedrockSummaryError
from aws_telegram_daily_brief.models.aws_report import AwsDailyReport
from aws_telegram_daily_brief.reporting.prompt_builder import PromptBuilder


@dataclass(frozen=True, slots=True)
class DailyBrief:
    text: str
    generated_by: str
    model_id: str | None = None
    fallback_used: bool = False
    warnings: tuple[str, ...] = ()
    usage: dict[str, int] = field(default_factory=dict)


class ReportSummarizer(Protocol):
    def summarize(self, report: AwsDailyReport) -> DailyBrief: ...


class DeterministicSummarizer:
    def summarize(self, report: AwsDailyReport) -> DailyBrief:
        summary = report.summary
        lines = [
            "☁️ AWS Daily Brief",
            "",
            (
                f"{summary.resources_detected} recursos detectados en "
                f"{summary.services_checked} servicios."
            ),
        ]
        skipped = [service for service in report.services if service.status.startswith("skipped_")]
        if skipped:
            lines.append(
                "ℹ️ "
                + ", ".join(service.service for service in skipped)
                + " omitido(s) por política automática."
            )
        if summary.warnings:
            lines.append(f"⚠️ Cobertura parcial: {summary.warnings} aviso(s).")
        else:
            lines.append("✓ Sin errores críticos detectados.")
        return DailyBrief("\n".join(lines), "deterministic", fallback_used=True)


class BedrockSummarizer:
    def __init__(
        self,
        settings: BedrockSettings,
        client: Any,
        prompt_builder: PromptBuilder | None = None,
        guard: AutomaticSafetyGuard | None = None,
    ) -> None:
        self.settings, self.client, self.prompt_builder = (
            settings,
            client,
            prompt_builder or PromptBuilder(),
        )
        self.invocations = 0
        self.guard = guard or AutomaticSafetyGuard()

    def summarize(self, report: AwsDailyReport) -> DailyBrief:
        if not self.settings.enabled:
            raise BedrockSummaryError("configuration_error")
        prompt = self.prompt_builder.build(report)
        if len(prompt) > self.prompt_builder.max_characters:
            raise BedrockSummaryError("prompt_too_large")
        self.invocations += 1
        if self.invocations > 1:
            raise BedrockSummaryError("invocation_limit")
        try:
            response = self.guard.execute_controlled_billable(
                self.client,
                operation_for("bedrock-runtime", "Converse"),
                modelId=self.settings.model_id,
                system=[{"text": self.prompt_builder.system_prompt}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={
                    "maxTokens": self.settings.max_output_tokens,
                    "temperature": self.settings.temperature,
                },
            )
        except (EndpointConnectionError, ReadTimeoutError):
            raise BedrockSummaryError("timeout") from None
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"ThrottlingException", "TooManyRequestsException"}:
                raise BedrockSummaryError("throttled") from None
            if code in {"ResourceNotFoundException", "ModelNotReadyException"}:
                raise BedrockSummaryError("model_unavailable") from None
            raise BedrockSummaryError(
                "permission_denied" if "Denied" in code else "service_error"
            ) from None
        except BotoCoreError:
            raise BedrockSummaryError("service_error") from None
        try:
            text = response["output"]["message"]["content"][0]["text"].strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            raise BedrockSummaryError("invalid_response") from None
        if not text or len(text) > 4096:
            raise BedrockSummaryError("empty_response")
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        return DailyBrief(
            text,
            "bedrock",
            self.settings.model_id,
            usage={key: value for key, value in usage.items() if isinstance(value, int)},
        )


class FallbackSummarizer:
    def __init__(self, primary: ReportSummarizer, fallback: DeterministicSummarizer) -> None:
        self.primary, self.fallback = primary, fallback

    def summarize(self, report: AwsDailyReport) -> DailyBrief:
        try:
            return self.primary.summarize(report)
        except BedrockSummaryError:
            return self.fallback.summarize(report)
