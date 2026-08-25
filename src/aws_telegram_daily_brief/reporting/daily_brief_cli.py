"""Render a local deterministic brief without sending Telegram or invoking Bedrock."""

import sys

from aws_telegram_daily_brief.config import Settings
from aws_telegram_daily_brief.llm.summarizer import DeterministicSummarizer
from aws_telegram_daily_brief.models.aws_report import AwsDailyReport


def main() -> None:
    text = (
        DeterministicSummarizer()
        .summarize(AwsDailyReport.empty(Settings.from_environment().aws_region))
        .text
    )
    sys.stdout.buffer.write(f"{text}\n".encode())
