"""Small, audited allowlist for automatic AWS report collection."""

from dataclasses import dataclass
from typing import Literal

CostClassification = Literal["free_verified", "potentially_billable", "unknown", "write"]


@dataclass(frozen=True, slots=True)
class AwsOperation:
    service: str
    operation: str
    method: str
    purpose: str
    access: Literal["read", "write"]
    cost_classification: CostClassification
    sensitive_data_risk: Literal["low", "high"]
    verified_at: str

    @property
    def automatic_allowed(self) -> bool:
        return (
            self.access == "read"
            and self.cost_classification == "free_verified"
            and self.sensitive_data_risk == "low"
        )


OPERATIONS = (
    AwsOperation(
        "lambda",
        "ListFunctions",
        "list_functions",
        "daily_inventory",
        "read",
        "free_verified",
        "low",
        "2026-07-23",
    ),
    AwsOperation(
        "ec2",
        "DescribeInstances",
        "describe_instances",
        "daily_inventory",
        "read",
        "free_verified",
        "low",
        "2026-07-23",
    ),
    AwsOperation(
        "ec2",
        "DescribeVpcs",
        "describe_vpcs",
        "daily_inventory",
        "read",
        "free_verified",
        "low",
        "2026-07-23",
    ),
    AwsOperation(
        "ec2",
        "DescribeSubnets",
        "describe_subnets",
        "daily_inventory",
        "read",
        "free_verified",
        "low",
        "2026-07-23",
    ),
    AwsOperation(
        "ec2",
        "DescribeRouteTables",
        "describe_route_tables",
        "daily_inventory",
        "read",
        "free_verified",
        "low",
        "2026-07-23",
    ),
    AwsOperation(
        "ec2",
        "DescribeInternetGateways",
        "describe_internet_gateways",
        "daily_inventory",
        "read",
        "free_verified",
        "low",
        "2026-07-23",
    ),
    AwsOperation(
        "s3",
        "ListBuckets",
        "list_buckets",
        "daily_inventory",
        "read",
        "potentially_billable",
        "low",
        "2026-07-23",
    ),
    AwsOperation(
        "cloudformation",
        "DescribeStacks",
        "describe_stacks",
        "daily_inventory",
        "read",
        "unknown",
        "low",
        "",
    ),
)


def operation_for(service: str, operation: str) -> AwsOperation:
    for item in OPERATIONS:
        if item.service == service and item.operation == operation:
            return item
    raise ValueError(f"Unregistered AWS operation: {service}.{operation}")
