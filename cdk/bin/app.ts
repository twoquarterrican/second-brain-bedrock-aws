import * as cdk from 'aws-cdk-lib';
import {SecondBrainStack} from "../lib/stacks/second-brain-stack";
import {App} from "aws-cdk-lib";

const env: cdk.Environment = {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'us-west-2', // Bedrock is only available in select regions
};

const app = new App();
new SecondBrainStack(app, 'SecondBrainStack', {env, description: 'Main infrastructure for Second Brain'});
app.synth()
