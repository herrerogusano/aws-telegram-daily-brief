"""Normalized report data without SDK response objects."""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

CoverageStatus = Literal[
    "checked",
    "empty",
    "skipped_by_cost_policy",
    "skipped_unknown_cost",
    "permission_denied",
    "timeout",
    "unavailable",
    "error",
]


@dataclass(frozen=True, slots=True)
class ResourceSummary:
    service: str
    resource_type: str
    name: str
    region: str
    state: str | None
    details: dict[str, str] = field(default_factory=dict)
    cost_risk_indicators: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ServiceReport:
    service: str
    status: CoverageStatus
    resources: tuple[ResourceSummary, ...] = ()
    reason: str | None = None
    error_kind: str | None = None


@dataclass(frozen=True, slots=True)
class DailyReportSummary:
    resources_detected: int
    services_checked: int
    services_skipped: int
    warnings: int


@dataclass(frozen=True, slots=True)
class AwsDailyReport:
    generated_at: datetime
    regions: tuple[str, ...]
    summary: DailyReportSummary
    services: tuple[ServiceReport, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["generated_at"] = self.generated_at.isoformat()
        data["regions"] = list(self.regions)
        return data

    @classmethod
    def empty(cls, region: str) -> "AwsDailyReport":
        return cls(datetime.now(UTC), (region,), DailyReportSummary(0, 0, 0, 0), ())
