# AWS Telegram Daily Brief

## Goal

A small serverless service that will send a concise daily view of an AWS account to Telegram.

## Architecture

`EventBridge (future) -> Lambda -> AWS APIs via Boto3 -> DailyAwsReport -> Bedrock or deterministic formatter -> Telegram`.

## Current status

**Phase 0 — design and bootstrap.** No AWS queries, Telegram messages, Bedrock invocations, schedule, or deployment exist yet.

## Stack

Python 3.12, uv, Boto3, AWS SAM, AWS Lambda, pytest, Ruff, and mypy. The production region is `eu-west-1`.

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

## Roadmap

Phase 1 adds a local Telegram boundary; Phase 2 builds the safe AWS report; later phases add Bedrock, deployment, scheduling, security controls, observability, CI/CD, and closure. See the vault documentation for the complete roadmap.

