"""Small collectors that only use registered operations through the guard."""

from __future__ import annotations

from typing import Any

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
)

from aws_telegram_daily_brief.aws.guard import AutomaticSafetyGuard
from aws_telegram_daily_brief.aws.operations import operation_for
from aws_telegram_daily_brief.models.aws_report import (
    CoverageStatus,
    ResourceSummary,
    ServiceReport,
)


def _error_report(service: str, error: Exception) -> ServiceReport:
    if isinstance(error, NoCredentialsError):
        return ServiceReport(service, "unavailable", error_kind="credentials_error")
    if isinstance(error, EndpointConnectionError):
        return ServiceReport(service, "timeout", error_kind="endpoint_error")
    if isinstance(error, ClientError):
        code = str(error.response.get("Error", {}).get("Code", ""))
        return ServiceReport(
            service,
            "permission_denied" if "Denied" in code else "error",
            error_kind=code or "service_error",
        )
    if isinstance(error, BotoCoreError):
        return ServiceReport(service, "error", error_kind="service_error")
    return ServiceReport(service, "error", error_kind="invalid_response")


class LambdaCollector:
    def __init__(self, client: Any, region: str, guard: AutomaticSafetyGuard) -> None:
        self.client, self.region, self.guard = client, region, guard

    def collect(self) -> ServiceReport:
        try:
            response = self.guard.execute(self.client, operation_for("lambda", "ListFunctions"))
            functions = response.get("Functions")
            if not isinstance(functions, list):
                raise ValueError("invalid Lambda response")
            resources = tuple(
                ResourceSummary(
                    "lambda",
                    "function",
                    str(item["FunctionName"]),
                    self.region,
                    str(item.get("State", "active")),
                    {"runtime": str(item.get("Runtime", "unknown"))},
                )
                for item in functions
                if isinstance(item, dict) and isinstance(item.get("FunctionName"), str)
            )
            return ServiceReport("lambda", "checked" if resources else "empty", resources)
        except Exception as error:
            return _error_report("lambda", error)


class Ec2Collector:
    _collections = (
        ("DescribeInstances", "Reservations", "instance", "Instances"),
        ("DescribeVpcs", "Vpcs", "vpc", "Vpcs"),
        ("DescribeSubnets", "Subnets", "subnet", "Subnets"),
        ("DescribeRouteTables", "RouteTables", "route_table", "RouteTables"),
        ("DescribeInternetGateways", "InternetGateways", "internet_gateway", "InternetGateways"),
    )

    def __init__(self, client: Any, region: str, guard: AutomaticSafetyGuard) -> None:
        self.client, self.region, self.guard = client, region, guard

    def collect(self) -> ServiceReport:
        resources: list[ResourceSummary] = []
        try:
            for operation, key, resource_type, nested in self._collections:
                response = self.guard.execute(self.client, operation_for("ec2", operation))
                items = response.get(key, [])
                if not isinstance(items, list):
                    raise ValueError("invalid EC2 response")
                if operation == "DescribeInstances":
                    items = [
                        instance
                        for reservation in items
                        if isinstance(reservation, dict)
                        for instance in reservation.get(nested, [])
                    ]
                for item in items:
                    if isinstance(item, dict):
                        identifier = next(
                            (
                                str(value)
                                for name, value in item.items()
                                if name.endswith("Id") and isinstance(value, str)
                            ),
                            resource_type,
                        )
                        state = (
                            str(item.get("State", {}).get("Name"))
                            if isinstance(item.get("State"), dict)
                            else None
                        )
                        indicators = (
                            ("compute_resource_running",)
                            if resource_type == "instance" and state == "running"
                            else ()
                        )
                        resources.append(
                            ResourceSummary(
                                "ec2",
                                resource_type,
                                identifier,
                                self.region,
                                state,
                                cost_risk_indicators=indicators,
                            )
                        )
            return ServiceReport("ec2", "checked" if resources else "empty", tuple(resources))
        except Exception as error:
            return _error_report("ec2", error)


class SkippedCollector:
    def __init__(self, service: str, operation: str) -> None:
        self.service, self.operation = service, operation

    def collect(self) -> ServiceReport:
        spec = operation_for(self.service, self.operation)
        status: CoverageStatus = (
            "skipped_by_cost_policy"
            if spec.cost_classification == "potentially_billable"
            else "skipped_unknown_cost"
        )
        return ServiceReport(
            self.service,
            status,
            reason=f"{spec.operation} is not allowed in automatic free-only mode",
        )
