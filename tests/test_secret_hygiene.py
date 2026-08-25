from pathlib import Path


def test_example_environment_file_contains_no_secret_value() -> None:
    content = Path(".env.example").read_text(encoding="utf-8")
    assert "TELEGRAM_BOT_TOKEN=" not in content
    assert "AKIA" not in content
