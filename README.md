# AWS Telegram Daily Brief

## Goal

A small serverless service that will send a concise daily view of an AWS account to Telegram.

## Architecture

`EventBridge (future) -> Lambda -> AWS APIs via Boto3 -> DailyAwsReport -> Bedrock or deterministic formatter -> Telegram`.

## Current status

**Phase 1 — local Telegram integration.** A deliberately explicit local command can now send one controlled plain-text Telegram message. Lambda remains disconnected from Telegram.

## Stack

Python 3.12, uv, Boto3, httpx, AWS SAM, AWS Lambda, pytest, Ruff, and mypy. The production region is `eu-west-1`.

## Safety

The scheduled workflow will only run operations confirmed as free and read-only. Potentially billable, unknown-cost, and write operations are excluded. Cost Explorer is not part of the automated report. Secrets are never committed.

## Development

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
sam validate
```

The minimum handler can be exercised with `uv run python -c "from aws_telegram_daily_brief.handler import lambda_handler; print(lambda_handler({}, None))"`.

## Telegram local setup

1. Create a bot through [BotFather](https://t.me/BotFather) and copy its token locally.
2. Start a chat with the bot (or add it to the destination group) and obtain the numeric chat ID manually. A common method is to send the bot a message and inspect `getUpdates` locally; do not store received messages or leave polling enabled.
3. Create a local `.env` file from `.env.example`. It is ignored by Git. Keep `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` out of all documentation, tests, and logs.
4. Send one explicit test message:

```powershell
uv run --env-file .env telegram-test
```

This command has no retries and sends only `AWS Telegram Daily Brief` followed by a short confirmation. Unit tests never contact Telegram.

Troubleshooting: `401` usually means an invalid token; `400` means invalid parameters; `403` can mean the bot is blocked or the chat is inaccessible; and a timeout indicates a Telegram or network problem. Other Telegram responses are reported generically without assuming their cause.

The local environment-variable approach is development-only. Before AWS deployment, the bot token must move to a secure AWS secret store; it must never be placed in `template.yaml`.

## Roadmap

Phase 2 builds the safe AWS report; later phases add Bedrock, deployment, scheduling, security controls, observability, CI/CD, and closure. See the vault documentation for the complete roadmap.
