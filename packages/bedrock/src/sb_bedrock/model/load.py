from strands.models import BedrockModel

# original from quickstart is Claude Sonnet 4.5
# Uses global inference profile for Claude Sonnet 4.5
# https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html
# MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

# see https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/model-catalog/serverless/anthropic.claude-3-5-haiku-20241022-v1:0
MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"


def load_model() -> BedrockModel:
    """
    Get Bedrock model client.
    Uses IAM authentication via the execution role.
    """
    return BedrockModel(model_id=MODEL_ID)
