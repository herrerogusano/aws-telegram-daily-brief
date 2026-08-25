from aws_telegram_daily_brief import DailyAwsReport


def test_package_exports_daily_report() -> None:
    assert DailyAwsReport.__name__ == "DailyAwsReport"
