import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

/**
 * StorageStack - Shared data storage for Second Brain
 *
 * Contains all persistent storage resources used by both:
 * - Application (message handler, processor)
 * - Bedrock agent runtime
 *
 * This stack has no dependencies and is deployed first.
 * Both ApplicationStack and BedrockStack depend on this.
 */
export class SecondBrainStorage extends Construct {
  public readonly dataTable: dynamodb.Table;
  public readonly dataBucket: s3.Bucket;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    /**
     * DynamoDB Table: second-brain
     * Single table with flexible PK/SK patterns
     * Shared by all components of the system
     */
    this.dataTable = new dynamodb.Table(this, 'DataTable', {
      tableName: 'second-brain',
      partitionKey: {
        name: 'PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'SK',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Add Global Secondary Index for flexible queries by item type/status/category
    // Models define their own GSI1PK and GSI1SK values
    this.dataTable.addGlobalSecondaryIndex({
      indexName: 'GSI1',
      partitionKey: {
        name: 'GSI1PK',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'GSI1SK',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Export table name for cross-stack references
    new cdk.CfnOutput(this, 'DataTableName', {
      value: this.dataTable.tableName,
      exportName: 'SecondBrainDataTableName',
      description: 'Name of main data table',
    });

    /**
     * S3 Bucket: second-brain-data
     * Immutable raw events + vector embeddings
     * Shared by all components of the system
     */
    this.dataBucket = new s3.Bucket(this, 'DataBucket', {
      bucketName: 'second-brain-data-twoquarterrican',
      versioned: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
    });

    // Add lifecycle rule: Intelligent-Tiering after 30 days
    this.dataBucket.addLifecycleRule({
      transitions: [
        {
          storageClass: s3.StorageClass.INTELLIGENT_TIERING,
          transitionAfter: cdk.Duration.days(30),
        },
      ],
    });

    // Export bucket name for cross-stack references
    new cdk.CfnOutput(this, 'DataBucketName', {
      value: this.dataBucket.bucketName,
      exportName: 'SecondBrainDataBucketName',
      description: 'Name of data storage bucket',
    });
  }
}
