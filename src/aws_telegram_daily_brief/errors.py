"""Small, explicit error vocabulary for future boundary layers."""


class ConfigurationError(ValueError):
    """Raised when safe runtime configuration is invalid."""


class AwsCollectionError(RuntimeError):
    """Raised when an AWS collection boundary cannot provide data."""


class BedrockSummaryError(RuntimeError):
    """Raised when the optional Bedrock summarizer fails."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(f"Bedrock summary failed ({kind})")


class TelegramNotificationError(RuntimeError):
    """Raised when the Telegram notification boundary fails."""

    def __init__(self, error_kind: str, status_code: int | None = None) -> None:
        self.error_kind = error_kind
        self.status_code = status_code
        details = f"Telegram notification failed ({error_kind})"
        if status_code is not None:
            details = f"{details}; status_code={status_code}"
        super().__init__(details)
