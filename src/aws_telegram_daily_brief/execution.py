"""Small, safe execution model used for logs and Lambda responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo


class ExecutionStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    DUPLICATE_SUSPECTED = "duplicate_suspected"


class ErrorComponent(StrEnum):
    CONFIGURATION = "configuration"
    AWS_COLLECTION = "aws_collection"
    BEDROCK = "bedrock"
    TELEGRAM = "telegram"
    SECRET_PROVIDER = "secret_provider"
    TIME_BUDGET = "time_budget"
    SCHEDULER = "scheduler"
    IDEMPOTENCY = "idempotency"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class ExecutionError:
    code: str
    component: ErrorComponent
    retryable: bool
    message: str


@dataclass(slots=True)
class ExecutionResult:
    execution_id: str
    report_date: str
    trigger_type: str
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    report_status: str = "complete"
    summary_source: str = "deterministic"
    notification_status: str = "not_requested"
    duplicate_status: str = "not_detected"
    warnings: list[str] = field(default_factory=list)
    errors: list[ExecutionError] = field(default_factory=list)
    metrics: dict[str, int | bool] = field(default_factory=dict)

    def partial(self, error: ExecutionError) -> None:
        self.errors.append(error)
        if self.status == ExecutionStatus.SUCCESS:
            self.status = ExecutionStatus.PARTIAL

    def response(self, report_summary: dict[str, object]) -> dict[str, Any]:
        return {
            "status": self.status,
            "execution_id": self.execution_id,
            "report_date": self.report_date,
            "trigger_type": self.trigger_type,
            "report_status": self.report_status,
            "summary_source": self.summary_source,
            "notification_status": self.notification_status,
            "duplicate_status": self.duplicate_status,
            "report": report_summary,
            "errors": [
                {"code": error.code, "component": error.component, "retryable": error.retryable}
                for error in self.errors
            ],
            "metrics": self.metrics,
        }


def madrid_report_date(now: datetime | None = None) -> str:
    current = now or datetime.now(tz=ZoneInfo("Europe/Madrid"))
    return current.astimezone(ZoneInfo("Europe/Madrid")).date().isoformat()
