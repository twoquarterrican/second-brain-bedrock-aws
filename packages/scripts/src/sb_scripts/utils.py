"""Common utility functions for scripts."""

import os
from functools import lru_cache
from pathlib import Path

import boto3
from dotenv import load_dotenv


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


def load_env(env_file: Path | str | None = None) -> None:
    """
    Load environment variables from .env files using dotenv.

    Loads in order:
    1. Base .env file (or specified env_file)
    2. .env.local (if it exists) - allows local overrides

    Args:
        env_file: Path to base .env file. If None, looks for .env in current directory.
    """
    if env_file is None:
        env_file = Path(".env")
    else:
        env_file = Path(env_file)

    # Load base .env file
    load_dotenv(env_file, override=False)

    # Load .env.local if it exists (allows local development overrides)
    env_local = env_file.parent / f"{env_file.stem}.local{env_file.suffix}"
    if env_local.exists():
        load_dotenv(env_local, override=True)


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
