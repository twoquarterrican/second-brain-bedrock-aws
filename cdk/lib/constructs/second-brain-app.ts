import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import {Construct} from 'constructs';
import * as path from 'path';
import * as fs from 'node:fs';
import {LambdaLayer} from './lambda-layer';

/**
 * ApplicationStack - Main infrastructure for Second Brain
 *
 * Depends on: StorageStack (for table and bucket)
 *
 * Contains:
 * - SQS Queue for async message processing
 * - Lambda Function URL for Telegram webhook
 * - Message Handler Lambda for webhook entry point
 * - Processing Lambda for async workflow
 * - IAM roles with least privilege
 * - Dead Letter Queue for failed messages
 */
export interface Props {
    dataTable: dynamodb.Table;
    dataBucket: s3.Bucket;
    bedrockAgentFunction: lambda.IFunction;
}

export class SecondBrainApp extends Construct {
    public dataTable: dynamodb.Table;
    public dataBucket: s3.Bucket;
    public messageQueue: sqs.Queue;
    public messageHandlerFunction: lambda.Function;
    public processingFunction: lambda.Function;
    public messageHandlerUrl: lambda.FunctionUrl;

    constructor(scope: Construct, id: string, props: Props) {
        super(scope, id);

        // Get Telegram secret token - required for webhook security
        const telegramSecretToken = process.env.TELEGRAM_SECRET_TOKEN;
        if (!telegramSecretToken) {
            throw new Error(
                'TELEGRAM_SECRET_TOKEN environment variable is not set. ' +
                'Please add it to your .env or .env.local file (required for webhook security).'
            );
        }

        // Use shared storage from StorageStack
        this.dataTable = props.dataTable;
        this.dataBucket = props.dataBucket;

        // ===== RESPONSE QUEUE =====

        /**
         * SQS Response Queue
         * For sending processed results back to users
         */
        const responseQueue = new sqs.Queue(this, 'ResponseQueue', {
            queueName: 'second-brain-responses',
            visibilityTimeout: cdk.Duration.minutes(5),
            retentionPeriod: cdk.Duration.hours(4),
            removalPolicy: cdk.RemovalPolicy.DESTROY,
        });

        new cdk.CfnOutput(this, 'ResponseQueueUrl', {
            value: responseQueue.queueUrl,
            exportName: 'SecondBrainResponseQueueUrl',
            description: 'URL of response queue',
        });

        // ===== ASYNC PROCESSING LAYER =====

        /**
         * SQS Dead Letter Queue
         * Captures messages that fail processing after max retries
         */
        const messageQueueDLQ = new sqs.Queue(this, 'MessageQueueDLQ', {
            queueName: 'second-brain-messages-dlq',
            retentionPeriod: cdk.Duration.days(14),
            removalPolicy: cdk.RemovalPolicy.DESTROY,
        });

        new cdk.CfnOutput(this, 'MessageQueueDLQUrl', {
            value: messageQueueDLQ.queueUrl,
            exportName: 'SecondBrainMessageQueueDLQUrl',
            description: 'URL of message processing DLQ',
        });

        /**
         * SQS Queue: Message Processing Queue
         * Decouples webhook from async processing
         * Allows retry and batching
         * Failed messages move to DLQ after 3 receive attempts
         */
        this.messageQueue = new sqs.Queue(this, 'MessageQueue', {
            queueName: 'second-brain-messages',
            visibilityTimeout: cdk.Duration.minutes(5),
            retentionPeriod: cdk.Duration.hours(1),
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            deadLetterQueue: {
                queue: messageQueueDLQ,
                maxReceiveCount: 3,
            },
        });

        new cdk.CfnOutput(this, 'MessageQueueUrl', {
            value: this.messageQueue.queueUrl,
            exportName: 'SecondBrainMessageQueueUrl',
            description: 'URL of message processing queue',
        });

        // ===== LAMBDA LAYER =====

        /**
         * Lambda Layer
         * Contains all dependencies and shared libraries
         */
        const lambdaLayer = new LambdaLayer(this, 'LambdaLayer', {
            appName: 'second-brain',
        });

        // Get project root from context for unified code asset
        const projectRoot = this.node.tryGetContext('ProjectRootPath');
        if (!projectRoot || !fs.existsSync(projectRoot)) {
            throw new Error(
                `ProjectRootPath context variable not set or invalid: ${projectRoot}`
            );
        }

        const lambdaDir = path.join(projectRoot, 'packages', 'lambda');
        if (!fs.existsSync(lambdaDir)) {
            throw new Error(`Lambda directory not found at ${lambdaDir}`);
        }

        // Shared Lambda code asset
        const lambdaCode = lambda.Code.fromAsset(lambdaDir);

        // ===== API LAYER =====

        /**
         * Lambda: Message Handler
         * Entry point for Telegram webhook
         * - Saves raw message to S3 (immutable)
         * - Saves metadata to DynamoDB
         * - Queues for async processing
         * - Returns 200 OK immediately
         */
        const messageHandlerLogGroup = new logs.LogGroup(
            this,
            'MessageHandlerLogGroup',
            {
                logGroupName: '/aws/lambda/second-brain-message-handler',
                retention: logs.RetentionDays.ONE_WEEK,
                removalPolicy: cdk.RemovalPolicy.DESTROY,
            }
        );

        this.messageHandlerFunction = new lambda.Function(this, 'MessageHandler', {
            functionName: 'second-brain-message-handler',
            runtime: lambda.Runtime.PYTHON_3_13,
            handler: 'sb_lambda.message_handler.index.lambda_handler',
            code: lambdaCode,
            timeout: cdk.Duration.seconds(10),
            memorySize: 256,
            layers: [lambdaLayer.layer],
            environment: {
                DYNAMODB_TABLE_NAME: this.dataTable.tableName,
                S3_BUCKET_NAME: this.dataBucket.bucketName,
                MESSAGE_QUEUE_URL: this.messageQueue.queueUrl,
                TELEGRAM_SECRET_TOKEN: telegramSecretToken,
            },
            logGroup: messageHandlerLogGroup,
            loggingFormat: lambda.LoggingFormat.JSON,
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
        const processingFunctionLogGroup = new logs.LogGroup(
            this,
            'ProcessingFunctionLogGroup',
            {
                logGroupName: '/aws/lambda/second-brain-processor',
                retention: logs.RetentionDays.ONE_WEEK,
                removalPolicy: cdk.RemovalPolicy.DESTROY,
            }
        );

        const processingEnv: { [key: string]: string } = {
            DYNAMODB_TABLE_NAME: this.dataTable.tableName,
            S3_BUCKET_NAME: this.dataBucket.bucketName,
            RESPONSE_QUEUE_URL: responseQueue.queueUrl,
            BEDROCK_AGENT_FUNCTION_NAME: props.bedrockAgentFunction.functionName,
        };

        this.processingFunction = new lambda.Function(this, 'ProcessingFunction', {
            functionName: 'second-brain-processor',
            runtime: lambda.Runtime.PYTHON_3_13,
            handler: 'sb_lambda.processor.index.lambda_handler',
            code: lambdaCode,
            timeout: cdk.Duration.minutes(5),
            memorySize: 512,
            layers: [lambdaLayer.layer],
            environment: processingEnv,
            logGroup: processingFunctionLogGroup,
            loggingFormat: lambda.LoggingFormat.JSON,
        });

        // Grant permissions to processing function
        this.dataTable.grantReadWriteData(this.processingFunction);
        this.dataBucket.grantRead(this.processingFunction, 'raw-events/*');
        this.messageQueue.grantConsumeMessages(this.processingFunction);
        responseQueue.grantSendMessages(this.processingFunction);

        // Grant invoke permission to Bedrock agent Lambda
        props.bedrockAgentFunction.grantInvoke(this.processingFunction);

        // Wire SQS to Lambda
        const {SqsEventSource} = require('aws-cdk-lib/aws-lambda-event-sources');
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
    }
}
