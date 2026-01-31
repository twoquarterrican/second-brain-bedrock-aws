import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

/**
 * Stack for DynamoDB database resources
 */
export class DatabaseStack extends cdk.Stack {
  public knowledgeTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Knowledge base table with ID and created_at as keys
    this.knowledgeTable = new dynamodb.Table(this, 'KnowledgeTable', {
      partitionKey: {
        name: 'id',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'created_at',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      pointInTimeRecovery: true,
      stream: dynamodb.StreamSpecification.NEW_AND_OLD_IMAGES,
    });

    // Add global secondary index for user queries
    this.knowledgeTable.addGlobalSecondaryIndex({
      indexName: 'UserIdIndex',
      partitionKey: {
        name: 'user_id',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Export table name for cross-stack references
    new cdk.CfnOutput(this, 'KnowledgeTableName', {
      value: this.knowledgeTable.tableName,
      exportName: 'SecondBrainKnowledgeTableName',
      description: 'Name of the DynamoDB knowledge base table',
    });

    // Export table ARN
    new cdk.CfnOutput(this, 'KnowledgeTableArn', {
      value: this.knowledgeTable.tableArn,
      exportName: 'SecondBrainKnowledgeTableArn',
      description: 'ARN of the DynamoDB knowledge base table',
    });
  }
}
