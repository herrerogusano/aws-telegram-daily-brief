"""Defence-in-depth gates for the audited runtime operation manifest."""

from typing import Any

from aws_telegram_daily_brief.aws.operations import AwsOperation, OperationClassification


class AutomaticSafetyGuard:
    def execute(self, client: Any, operation: AwsOperation, **kwargs: Any) -> dict[str, Any]:
        return self._execute(client, operation, {"free_verified_read"}, **kwargs)

    def execute_secret_read(
        self, client: Any, operation: AwsOperation, **kwargs: Any
    ) -> dict[str, Any]:
        return self._execute(client, operation, {"operational_secret_read"}, **kwargs)

    def execute_controlled_billable(
        self, client: Any, operation: AwsOperation, **kwargs: Any
    ) -> dict[str, Any]:
        return self._execute(client, operation, {"controlled_billable"}, **kwargs)

    @staticmethod
    def _execute(
        client: Any,
        operation: AwsOperation,
        allowed: set[OperationClassification],
        **kwargs: Any,
    ) -> dict[str, Any]:
        if operation.classification not in allowed:
            raise OperationBlockedError(operation)
        try:
            result = getattr(client, operation.method)(**kwargs)
        except AttributeError:
            raise ValueError("AWS client does not support registered operation") from None
        if not isinstance(result, dict):
            raise ValueError("AWS operation returned an invalid response")
        return result


class OperationBlockedError(RuntimeError):
    def __init__(self, operation: AwsOperation) -> None:
        self.operation = operation
        super().__init__(f"Operation blocked by policy: {operation.service}.{operation.operation}")
