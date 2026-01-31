"""CDK stack for database resources (DynamoDB, etc)."""

import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb


class DatabaseStack(cdk.Stack):
    """Stack for database resources."""

    def __init__(self, scope: cdk.App, id: str, **kwargs) -> None:
        """Initialize database stack."""
        super().__init__(scope, id, **kwargs)

        # Knowledge base table
        self.knowledge_table = dynamodb.Table(
            self,
            "KnowledgeTable",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # Add indexes for common queries
        self.knowledge_table.add_global_secondary_index(
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            index_name="UserIdIndex",
        )

        # Export table name
        cdk.CfnOutput(
            self,
            "KnowledgeTableName",
            value=self.knowledge_table.table_name,
        )
