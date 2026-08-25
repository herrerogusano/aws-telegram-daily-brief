from typing import Any

from aws_telegram_daily_brief import handler


class FakeClient:
    def list_functions(self) -> dict[str, object]:
        return {"Functions": []}

    def describe_instances(self) -> dict[str, object]:
        return {"Reservations": []}

    def describe_vpcs(self) -> dict[str, object]:
        return {"Vpcs": []}

    def describe_subnets(self) -> dict[str, object]:
        return {"Subnets": []}

    def describe_route_tables(self) -> dict[str, object]:
        return {"RouteTables": []}

    def describe_internet_gateways(self) -> dict[str, object]:
        return {"InternetGateways": []}


class FakeFactory:
    def __init__(self, region: str) -> None:
        pass

    def create(self, service: str) -> FakeClient:
        return FakeClient()


def test_handler_returns_safe_structured_payload(monkeypatch: Any) -> None:
    monkeypatch.setattr(handler, "AwsClientFactory", FakeFactory)
    response = handler.lambda_handler({}, None)
    assert response["status"] == "partial"
    assert response["brief"]["generated_by"] == "deterministic"


def test_handler_does_not_need_event_shape(monkeypatch: Any) -> None:
    monkeypatch.setattr(handler, "AwsClientFactory", FakeFactory)
    assert handler.lambda_handler({"unused": True}, object())["report"]["resources_detected"] == 0
