from pathlib import Path


def _workflow(name: str) -> str:
    return (Path(".github/workflows") / name).read_text(encoding="utf-8")


def test_ci_has_no_aws_credentials_or_deployment() -> None:
    workflow = _workflow("ci.yml")
    assert "pull_request:" in workflow and "branches: [master]" in workflow
    assert "id-token: write" not in workflow
    assert "configure-aws-credentials" not in workflow
    assert "sam deploy" not in workflow
    assert "uv sync --locked" in workflow


def test_deploy_is_master_only_and_uses_oidc_after_quality_gates() -> None:
    workflow = _workflow("deploy.yml")
    assert "branches: [master]" in workflow
    assert "id-token: write" in workflow
    assert "role-to-assume:" in workflow
    assert "environment: production" not in workflow
    assert "aws-access-key-id:" not in workflow
    assert "aws-secret-access-key:" not in workflow
    assert "sam deploy" in workflow
    assert workflow.index("uv run pytest") < workflow.index("configure-aws-credentials")
    assert "cancel-in-progress: false" in workflow


def test_bootstrap_reuses_provider_and_limits_trust_to_repository_branch() -> None:
    bootstrap = Path("infra/bootstrap/github-oidc.yaml").read_text(encoding="utf-8")
    assert "AWS::IAM::OIDCProvider" not in bootstrap
    assert "repo:${GitHubRepository}:ref:refs/heads/${DeploymentBranch}" in bootstrap
    assert "sts.amazonaws.com" in bootstrap
    assert "AdministratorAccess" not in bootstrap
    assert 'Action: "*"' not in bootstrap
    assert "ssm:GetParameter" not in bootstrap
    assert "bedrock:InvokeModel" not in bootstrap
