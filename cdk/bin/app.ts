import * as cdk from 'aws-cdk-lib';
import {SecondBrainStack} from "../lib/stacks/second-brain-stack";
import {App} from "aws-cdk-lib";

const app = new App();

// CDK needs both account and region. Account comes from CDK_DEFAULT_ACCOUNT env var
// which is set by the AWS SDK/CLI based on the current AWS credentials
const env: cdk.Environment = {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'us-west-2', // Bedrock is only available in select regions
};

new SecondBrainStack(app, 'SecondBrainStack', {env, description: 'Main infrastructure for Second Brain'});
app.synth()
