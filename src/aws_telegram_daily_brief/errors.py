"""Small, explicit error vocabulary for future boundary layers."""


class ConfigurationError(ValueError):
    """Raised when safe runtime configuration is invalid."""


class AwsCollectionError(RuntimeError):
    """Raised when an AWS collection boundary cannot provide data."""


class BedrockSummaryError(RuntimeError):
    """Raised when the optional Bedrock summarizer fails."""


class TelegramNotificationError(RuntimeError):
    """Raised when the Telegram notification boundary fails."""
