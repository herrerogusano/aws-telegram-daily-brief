from aws_telegram_daily_brief.handler import lambda_handler


def test_handler_returns_bootstrap_payload() -> None:
    response = lambda_handler({}, None)
    assert response == {"status": "ok", "message": "AWS Telegram Daily Brief initialized"}


def test_handler_does_not_need_event_shape() -> None:
    response = lambda_handler({"unused": True}, object())
    assert response["status"] == "ok"
