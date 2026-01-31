"""Main Bedrock application module."""

import os
from typing import Optional

import boto3
from dotenv import load_dotenv

load_dotenv()


class BedrockApp:
    """Main application for Bedrock-based second brain."""

    def __init__(self):
        """Initialize Bedrock application."""
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv(
            "AWS_BEDROCK_MODEL_ID",
            "anthropic.claude-3-sonnet-20240229-v1:0"
        )
        self.client = boto3.client("bedrock-runtime", region_name=self.region)

    def invoke_model(self, prompt: str) -> Optional[str]:
        """Invoke Bedrock model with given prompt."""
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=prompt.encode("utf-8"),
            )
            return response.get("body", {}).read().decode("utf-8")
        except Exception as e:
            print(f"Error invoking model: {e}")
            return None


def main():
    """Run the Bedrock application."""
    app = BedrockApp()
    print(f"Bedrock app initialized with model: {app.model_id}")


if __name__ == "__main__":
    main()
