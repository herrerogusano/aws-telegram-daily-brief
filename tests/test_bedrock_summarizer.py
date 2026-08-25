import pytest

from aws_telegram_daily_brief.config import BedrockSettings
from aws_telegram_daily_brief.errors import BedrockSummaryError
from aws_telegram_daily_brief.llm.summarizer import (
    BedrockSummarizer,
    DeterministicSummarizer,
    FallbackSummarizer,
)
from aws_telegram_daily_brief.models.aws_report import AwsDailyReport


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def converse(self, **kwargs: object) -> dict[str, object]:
        self.calls += 1
        return {
            "output": {"message": {"content": [{"text": "Resumen válido"}]}},
            "usage": {"inputTokens": 10, "outputTokens": 4},
        }


def test_disabled_uses_fallback_without_call() -> None:
    client = FakeClient()
    brief = FallbackSummarizer(
        BedrockSummarizer(BedrockSettings(enabled=False), client), DeterministicSummarizer()
    ).summarize(AwsDailyReport.empty("eu-west-1"))
    assert brief.generated_by == "deterministic" and client.calls == 0


def test_bedrock_single_call_and_usage() -> None:
    client = FakeClient()
    summarizer = BedrockSummarizer(BedrockSettings(enabled=True), client)
    assert summarizer.summarize(AwsDailyReport.empty("eu-west-1")).generated_by == "bedrock"
    with pytest.raises(BedrockSummaryError):
        summarizer.summarize(AwsDailyReport.empty("eu-west-1"))
