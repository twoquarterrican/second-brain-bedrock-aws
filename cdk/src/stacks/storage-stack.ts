import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

/**
 * Stack for S3 storage and vector database resources
 */
export class StorageStack extends cdk.Stack {
  public vectorBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // S3 bucket for documents, embeddings, and vectors
    this.vectorBucket = new s3.Bucket(this, 'VectorBucket', {
      versioned: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
    });

    // Add lifecycle rule for cost optimization
    // Move to Intelligent-Tiering after 30 days
    this.vectorBucket.addLifecycleRule({
      transitions: [
        {
          storageClass: s3.StorageClass.INTELLIGENT_TIERING,
          transitionAfter: cdk.Duration.days(30),
        },
      ],
    });

    // Export bucket name for cross-stack references
    new cdk.CfnOutput(this, 'VectorBucketName', {
      value: this.vectorBucket.bucketName,
      exportName: 'SecondBrainVectorBucketName',
      description: 'Name of the S3 vector storage bucket',
    });

    // Export bucket ARN
    new cdk.CfnOutput(this, 'VectorBucketArn', {
      value: this.vectorBucket.bucketArn,
      exportName: 'SecondBrainVectorBucketArn',
      description: 'ARN of the S3 vector storage bucket',
    });
  }
}
