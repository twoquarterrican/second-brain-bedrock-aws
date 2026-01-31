"""AWS CDK application for Second Brain infrastructure."""

import aws_cdk as cdk


class SecondBrainStack(cdk.Stack):
    """CDK Stack for Second Brain infrastructure."""

    def __init__(self, scope: cdk.App, id: str, **kwargs) -> None:
        """Initialize Second Brain stack."""
        super().__init__(scope, id, **kwargs)

        # Stack definitions will go here
        # - DynamoDB tables
        # - S3 buckets
        # - Lambda functions
        # - API Gateway
        # - IAM roles


def main():
    """Instantiate CDK app and stacks."""
    app = cdk.App()

    SecondBrainStack(
        app,
        "SecondBrainStack",
        description="Infrastructure for Second Brain Bedrock application",
    )

    app.synth()


if __name__ == "__main__":
    main()
