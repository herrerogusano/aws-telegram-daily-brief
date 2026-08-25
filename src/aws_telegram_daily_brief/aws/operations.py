"""Audited manifest of every AWS SDK operation reachable by the runtime."""

from dataclasses import dataclass
from typing import Literal

OperationClassification = Literal[
    "free_verified_read",
    "controlled_billable",
    "operational_secret_read",
    "write",
    "sensitive_read",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class AwsOperation:
    service: str
    operation: str
    method: str
    iam_action: str
    component: str
    classification: OperationClassification
    required: bool
    verified_at: str

    @property
    def automatic_allowed(self) -> bool:
        return self.classification == "free_verified_read"


def _op(
    service: str,
    operation: str,
    method: str,
    iam_action: str,
    component: str,
    classification: OperationClassification,
    required: bool,
    verified_at: str,
) -> AwsOperation:
    return AwsOperation(
        service, operation, method, iam_action, component, classification, required, verified_at
    )


OPERATIONS = (
    _op(
        "lambda",
        "ListFunctions",
        "list_functions",
        "lambda:ListFunctions",
        "LambdaCollector",
        "free_verified_read",
        True,
        "2026-07-23",
    ),
    _op(
        "ec2",
        "DescribeInstances",
        "describe_instances",
        "ec2:DescribeInstances",
        "Ec2Collector",
        "free_verified_read",
        True,
        "2026-07-23",
    ),
    _op(
        "ec2",
        "DescribeVpcs",
        "describe_vpcs",
        "ec2:DescribeVpcs",
        "Ec2Collector",
        "free_verified_read",
        True,
        "2026-07-23",
    ),
    _op(
        "ec2",
        "DescribeSubnets",
        "describe_subnets",
        "ec2:DescribeSubnets",
        "Ec2Collector",
        "free_verified_read",
        True,
        "2026-07-23",
    ),
    _op(
        "ec2",
        "DescribeRouteTables",
        "describe_route_tables",
        "ec2:DescribeRouteTables",
        "Ec2Collector",
        "free_verified_read",
        True,
        "2026-07-23",
    ),
    _op(
        "ec2",
        "DescribeInternetGateways",
        "describe_internet_gateways",
        "ec2:DescribeInternetGateways",
        "Ec2Collector",
        "free_verified_read",
        True,
        "2026-07-23",
    ),
    _op(
        "ssm",
        "GetParameter",
        "get_parameter",
        "ssm:GetParameter",
        "ParameterStoreTelegramConfigProvider",
        "operational_secret_read",
        True,
        "2026-08-25",
    ),
    _op(
        "bedrock-runtime",
        "Converse",
        "converse",
        "bedrock:InvokeModel",
        "BedrockSummarizer",
        "controlled_billable",
        False,
        "2026-08-25",
    ),
    _op(
        "s3",
        "ListBuckets",
        "list_buckets",
        "s3:ListAllMyBuckets",
        "SkippedCollector",
        "sensitive_read",
        False,
        "2026-07-23",
    ),
    _op(
        "cloudformation",
        "DescribeStacks",
        "describe_stacks",
        "cloudformation:DescribeStacks",
        "SkippedCollector",
        "unknown",
        False,
        "",
    ),
)


def operation_for(service: str, operation: str) -> AwsOperation:
    for item in OPERATIONS:
        if item.service == service and item.operation == operation:
            return item
    raise ValueError(f"Unregistered AWS operation: {service}.{operation}")
