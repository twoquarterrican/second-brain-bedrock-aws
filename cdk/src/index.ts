import * as cdk from 'aws-cdk-lib';
import { DatabaseStack } from './stacks/database-stack';
import { StorageStack } from './stacks/storage-stack';

/**
 * Second Brain CDK Application
 *
 * This app defines the core infrastructure for the Second Brain system:
 * - DynamoDB for knowledge base metadata and relationships
 * - S3 for document and vector storage
 * - Additional stacks can be added for AgentCore, Lambda, API Gateway, etc.
 */
class SecondBrainApp extends cdk.App {
  constructor() {
    super();

    const env: cdk.Environment = {
      account: process.env.CDK_DEFAULT_ACCOUNT,
      region: process.env.CDK_DEFAULT_REGION,
    };

    // Create shared infrastructure stacks
    new DatabaseStack(this, 'DatabaseStack', {
      env,
      description: 'DynamoDB tables for Second Brain knowledge base',
    });

    new StorageStack(this, 'StorageStack', {
      env,
      description: 'S3 buckets for Second Brain vector and document storage',
    });
  }
}

const app = new SecondBrainApp();
app.synth();
