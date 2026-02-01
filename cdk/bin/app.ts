import * as cdk from 'aws-cdk-lib';
import {SecondBrainStack} from "../lib/stacks/second-brain-stack";
import {App} from "aws-cdk-lib";

const app = new App();

// Get account from context (passed via CLI or env var)
const account = app.node.tryGetContext('AWS_ACCOUNT_ID') ||
                process.env.CDK_DEFAULT_ACCOUNT;

if (!account) {
  throw new Error(
    'AWS account ID not found. Set AWS_ACCOUNT_ID context or CDK_DEFAULT_ACCOUNT environment variable.'
  );
}

const env: cdk.Environment = {
    account,
    region: 'us-west-2', // Bedrock is only available in select regions
};

new SecondBrainStack(app, 'SecondBrainStack', {env, description: 'Main infrastructure for Second Brain'});
app.synth()
