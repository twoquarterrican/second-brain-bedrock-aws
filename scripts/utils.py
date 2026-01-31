"""Common utility functions for scripts."""

import os
from typing import Optional

import boto3


def get_aws_region() -> str:
    """Get AWS region from environment or default."""
    return os.getenv("AWS_REGION", "us-east-1")


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
