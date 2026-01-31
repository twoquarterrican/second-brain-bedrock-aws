"""CDK stack for storage resources (S3, etc)."""

import aws_cdk as cdk
from aws_cdk import aws_s3 as s3


class StorageStack(cdk.Stack):
    """Stack for storage resources."""

    def __init__(self, scope: cdk.App, id: str, **kwargs) -> None:
        """Initialize storage stack."""
        super().__init__(scope, id, **kwargs)

        # S3 bucket for documents and vectors
        self.vector_bucket = s3.Bucket(
            self,
            "VectorBucket",
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Add lifecycle rules for cost optimization
        self.vector_bucket.add_lifecycle_rule(
            transitions=[
                s3.Transition(
                    storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                    transition_after=cdk.Duration.days(30),
                )
            ]
        )

        # Export bucket name
        cdk.CfnOutput(
            self,
            "VectorBucketName",
            value=self.vector_bucket.bucket_name,
        )
