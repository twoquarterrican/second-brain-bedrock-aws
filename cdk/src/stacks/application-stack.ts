import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import * as path from 'path';

/**
 * ApplicationStack - Main infrastructure for Second Brain
 *
 * Contains:
 * - DynamoDB table (second-brain) for all data types
 * - S3 bucket (second-brain-data) with prefixes for immutable raw events
 * - SQS Queue for async message processing
 * - Lambda Function URL for Telegram webhook
 * - Processing Lambda for async workflow
 * - IAM roles with least privilege
 */
export class ApplicationStack extends cdk.Stack {
  public dataTable: dynamodb.Table;
  public dataBucket: s3.Bucket;
  public messageQueue: sqs.Queue;
  public messageHandlerFunction: lambda.Function;
  public processingFunction: lambda.Function;
  public messageHandlerUrl: lambda.FunctionUrl;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ===== DATA LAYER =====

    /**
     * DynamoDB Table: second-brain
     * Single table with flexible PK/SK patterns
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

      // TODO: Add GSI for type filtering if needed
      // GSI1: { PK: "type", SK: "user_id" } for queries by item type
    });

    // Export table name for Lambda functions
    new cdk.CfnOutput(this, 'DataTableName', {
      value: this.dataTable.tableName,
      exportName: 'SecondBrainDataTableName',
      description: 'Name of main data table',
    });

    /**
     * S3 Bucket: second-brain-data
     * Immutable raw events + vector embeddings
     */
    this.dataBucket = new s3.Bucket(this, 'DataBucket', {
      bucketName: 'second-brain-data',
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

    // Export bucket name
    new cdk.CfnOutput(this, 'DataBucketName', {
      value: this.dataBucket.bucketName,
      exportName: 'SecondBrainDataBucketName',
      description: 'Name of data storage bucket',
    });

    // ===== ASYNC PROCESSING LAYER =====

    /**
     * SQS Queue: Message Processing Queue
     * Decouples webhook from async processing
     * Allows retry and batching
     */
    this.messageQueue = new sqs.Queue(this, 'MessageQueue', {
      queueName: 'second-brain-messages',
      visibilityTimeout: cdk.Duration.minutes(5),
      messageRetentionPeriod: cdk.Duration.hours(1),
      removalPolicy: cdk.RemovalPolicy.DESTROY,

      // TODO: Add DLQ for failed messages
    });

    new cdk.CfnOutput(this, 'MessageQueueUrl', {
      value: this.messageQueue.queueUrl,
      exportName: 'SecondBrainMessageQueueUrl',
      description: 'URL of message processing queue',
    });

    // ===== API LAYER =====

    /**
     * Lambda: Message Handler
     * Entry point for Telegram webhook
     * - Saves raw message to S3 (immutable)
     * - Saves metadata to DynamoDB
     * - Queues for async processing
     * - Returns 200 OK immediately
     */
    this.messageHandlerFunction = new lambda.Function(this, 'MessageHandler', {
      functionName: 'second-brain-message-handler',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda/message_handler')),
      timeout: cdk.Duration.seconds(10),
      memorySize: 256,
      environment: {
        DYNAMODB_TABLE_NAME: this.dataTable.tableName,
        S3_BUCKET_NAME: this.dataBucket.bucketName,
        MESSAGE_QUEUE_URL: this.messageQueue.queueUrl,
        AWS_REGION: this.region,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // Grant permissions to message handler
    this.dataTable.grantWriteData(this.messageHandlerFunction);
    this.dataBucket.grantWrite(this.messageHandlerFunction, 'raw-events/*');
    this.messageQueue.grantSendMessages(this.messageHandlerFunction);

    // Function URL for Telegram webhook
    this.messageHandlerUrl = this.messageHandlerFunction.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
    });

    new cdk.CfnOutput(this, 'WebhookUrl', {
      value: this.messageHandlerUrl.url,
      exportName: 'SecondBrainWebhookUrl',
      description: 'Telegram webhook URL',
    });

    // ===== ASYNC PROCESSING LAYER =====

    /**
     * Lambda: Processing Function
     * Triggered by SQS messages
     * - Gets message from DynamoDB
     * - Invokes Bedrock agent
     * - Creates tasks/reminders
     * - Queues response
     */
    this.processingFunction = new lambda.Function(this, 'ProcessingFunction', {
      functionName: 'second-brain-processor',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda/processor')),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE_NAME: this.dataTable.tableName,
        S3_BUCKET_NAME: this.dataBucket.bucketName,
        BEDROCK_AGENT_FUNCTION_NAME: 'bedrock-agent-runtime', // TODO: Make parameterizable
        AWS_REGION: this.region,

        // TODO: Response queue URL
        // RESPONSE_QUEUE_URL: ???,
      },
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    // Grant permissions to processing function
    this.dataTable.grantReadWriteData(this.processingFunction);
    this.dataBucket.grantRead(this.processingFunction, 'raw-events/*');
    this.messageQueue.grantConsumeMessages(this.processingFunction);

    // TODO: Grant invoke permission to Bedrock agent Lambda
    // const bedrockAgentRole = iam.Role.fromRoleArn(...)
    // bedrockAgentRole.grantAssumeRole(this.processingFunction.grantPrincipal)

    // Wire SQS to Lambda
    const { SqsEventSource } = require('aws-cdk-lib/aws-lambda-event-sources');
    this.processingFunction.addEventSource(
      new SqsEventSource(this.messageQueue, {
        batchSize: 1,
        maxConcurrency: 5,
      })
    );

    // ===== OBSERVABILITY =====

    // TODO: CloudWatch Logs Insights dashboard
    // TODO: Custom metrics for processing latency
    // TODO: Alarms for Lambda errors

    // Export key values for use by other stacks/scripts
    new cdk.CfnOutput(this, 'StackExports', {
      value: JSON.stringify({
        dataTableName: this.dataTable.tableName,
        dataBucketName: this.dataBucket.bucketName,
        messageQueueUrl: this.messageQueue.queueUrl,
        webhookUrl: this.messageHandlerUrl.url,
      }),
      exportName: 'SecondBrainStackExports',
      description: 'Stack exports for reference',
    });
  }
}
