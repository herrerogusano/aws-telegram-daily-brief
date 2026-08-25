"""The normalized report passed between collection and presentation layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class DailyAwsReport:
    """A deliberately small, serializable, and Boto3-independent daily report."""

    generated_at: datetime
    region_scope: tuple[str, ...]
    inventory: dict[str, Any] = field(
        default_factory=lambda: {"total_resources": 0, "services": {}}
    )
    activity: dict[str, Any] = field(default_factory=dict)
    cost_risk: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    coverage: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(cls, region_scope: tuple[str, ...] = ("eu-west-1",)) -> DailyAwsReport:
        return cls(generated_at=datetime.now(UTC), region_scope=region_scope)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible data without AWS SDK response objects."""
        report = asdict(self)
        report["generated_at"] = self.generated_at.isoformat()
        report["region_scope"] = list(self.region_scope)
        report["warnings"] = list(self.warnings)
        report["errors"] = list(self.errors)
        return report
