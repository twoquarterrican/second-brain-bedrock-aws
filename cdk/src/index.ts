import * as cdk from 'aws-cdk-lib';
import { ApplicationStack } from './stacks/application-stack';

/**
 * Second Brain CDK Application
 *
 * This app defines the core infrastructure for the Second Brain system:
 * - Single ApplicationStack containing all resources:
 *   - DynamoDB table (second-brain) for all data types
 *   - S3 bucket (second-brain-data) with prefixes
 *   - SQS Queue for async message processing
 *   - Lambda Function URL for Telegram webhook
 *   - Processing Lambda for async workflow
 *   - IAM roles with least privilege
 *
 * Separate stack:
 * - bedrock/cdk contains AgentCore runtime (self-contained)
 *
 * Shared library:
 * - /lib/python/second_brain_core used by both stacks
 */
class SecondBrainApp extends cdk.App {
  constructor() {
    super();

    const env: cdk.Environment = {
      account: process.env.CDK_DEFAULT_ACCOUNT,
      region: process.env.CDK_DEFAULT_REGION,
    };

    // Create main application infrastructure
    new ApplicationStack(this, 'ApplicationStack', {
      env,
      description: 'Second Brain main infrastructure: DynamoDB, S3, Lambdas, SQS',
    });
  }
}

const app = new SecondBrainApp();
app.synth();
