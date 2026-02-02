"""Common utility functions for scripts."""

import os
from functools import lru_cache
from pathlib import Path

import boto3


def get_aws_region() -> str:
    """Get AWS region from environment or default."""
    return os.getenv("AWS_REGION", "us-west-2")


def get_bedrock_client():
    """Get Bedrock runtime client."""
    return boto3.client("bedrock-runtime", region_name=get_aws_region())


def get_dynamodb_resource():
    """Get DynamoDB resource."""
    return boto3.resource("dynamodb", region_name=get_aws_region())


def get_s3_client():
    """Get S3 client."""
    return boto3.client("s3", region_name=get_aws_region())


def get_lambda_client():
    """Get Lambda client."""
    return boto3.client("lambda", region_name=get_aws_region())


def get_environment() -> str:
    """Get deployment environment."""
    return os.getenv("ENVIRONMENT", "dev")


@lru_cache(maxsize=1)
def find_project_root(start_path: Path | None = None) -> Path:
    """
    Find the project root by walking up the directory tree looking for the workspace root.

    The workspace root is identified by a pyproject.toml file containing [tool.uv.workspace].
    Results are cached since the project root doesn't change during script execution.

    Args:
        start_path: Starting path to search from. Defaults to the current working directory.

    Returns:
        Path to the project root (workspace root directory).

    Raises:
        RuntimeError: If project root cannot be found.
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()
    while current != current.parent:
        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject) as f:
                if "[tool.uv.workspace]" in f.read():
                    return current
        current = current.parent

    raise RuntimeError(f"Could not find project root starting from {start_path}")
