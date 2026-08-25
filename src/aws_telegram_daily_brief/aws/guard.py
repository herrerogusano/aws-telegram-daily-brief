"""Central automatic free-only guard."""

from typing import Any

from aws_telegram_daily_brief.aws.operations import AwsOperation


class AutomaticSafetyGuard:
    def execute(self, client: Any, operation: AwsOperation, **kwargs: Any) -> dict[str, Any]:
        if not operation.automatic_allowed:
            raise OperationBlockedError(operation)
        result = getattr(client, operation.method)(**kwargs)
        if not isinstance(result, dict):
            raise ValueError("AWS operation returned an invalid response")
        return result


class OperationBlockedError(RuntimeError):
    def __init__(self, operation: AwsOperation) -> None:
        self.operation = operation
        super().__init__(
            f"Operation blocked by automatic policy: {operation.service}.{operation.operation}"
        )
