import pytest

from aws_telegram_daily_brief.aws.collectors import LambdaCollector, SkippedCollector
from aws_telegram_daily_brief.aws.guard import AutomaticSafetyGuard, OperationBlockedError
from aws_telegram_daily_brief.aws.operations import operation_for
from aws_telegram_daily_brief.reporting.builder import DailyReportBuilder


class LambdaClient:
    def list_functions(self) -> dict[str, object]:
        return {
            "Functions": [{"FunctionName": "brief", "Runtime": "python3.12", "State": "Active"}]
        }


def test_guard_blocks_s3_automatically() -> None:
    with pytest.raises(OperationBlockedError):
        AutomaticSafetyGuard().execute(object(), operation_for("s3", "ListBuckets"))


def test_lambda_collection_and_report_builder_are_normalized() -> None:
    report = LambdaCollector(LambdaClient(), "eu-west-1", AutomaticSafetyGuard()).collect()
    daily = DailyReportBuilder("eu-west-1").build(
        (report, SkippedCollector("s3", "ListBuckets").collect())
    )
    assert report.resources[0].name == "brief"
    assert daily.summary.resources_detected == 1
    assert daily.summary.services_skipped == 1
    assert daily.to_dict()["services"][1]["status"] == "skipped_by_cost_policy"
