import logging
from datetime import UTC, datetime

import pytest

from aws_telegram_daily_brief.execution import ExecutionResult, ExecutionStatus, madrid_report_date
from aws_telegram_daily_brief.observability import log_event


def test_report_date_uses_madrid_not_utc_boundary() -> None:
    assert madrid_report_date(datetime(2026, 8, 25, 23, 30, tzinfo=UTC)) == "2026-08-26"


def test_execution_response_excludes_internal_messages() -> None:
    result = ExecutionResult("safe-execution-id", "2026-08-25", "scheduled")
    response = result.response({"resources_detected": 0})
    assert response["status"] == ExecutionStatus.SUCCESS
    assert "brief" not in response and "warnings" not in response


def test_structured_log_filters_sensitive_fields(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        log_event(
            "execution_started",
            "safe-execution-id",
            "2026-08-25",
            token="never-log",
            chat_id="never-log",
            status="success",
        )
    record = caplog.records[-1]
    assert not hasattr(record, "token") and not hasattr(record, "chat_id")
    assert record.__dict__["execution_id"] == "safe-execution-id"
