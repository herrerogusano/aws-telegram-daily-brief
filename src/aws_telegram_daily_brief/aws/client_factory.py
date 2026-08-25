"""Boto3 construction with conservative timeouts and no import-time client."""

from typing import Any

import boto3
from botocore.config import Config


class AwsClientFactory:
    def __init__(self, region: str, profile_name: str | None = None) -> None:
        self._region = region
        self._profile_name = profile_name

    def create(self, service: str) -> Any:
        options: dict[str, str] = {"region_name": self._region}
        if self._profile_name:
            options["profile_name"] = self._profile_name
        session = boto3.Session(**options)
        return session.client(
            service,
            config=Config(
                connect_timeout=5, read_timeout=10, retries={"max_attempts": 0, "mode": "standard"}
            ),
        )

    def create_bedrock_runtime(self, *, timeout_seconds: float) -> Any:
        """Create a bounded inference client with no SDK retry attempts."""
        options: dict[str, str] = {"region_name": self._region}
        if self._profile_name:
            options["profile_name"] = self._profile_name
        return boto3.Session(**options).client(
            "bedrock-runtime",
            config=Config(
                connect_timeout=5,
                read_timeout=timeout_seconds,
                retries={"max_attempts": 0, "mode": "standard"},
            ),
        )
