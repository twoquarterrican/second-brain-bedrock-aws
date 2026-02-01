import * as cdk from 'aws-cdk-lib';
import {SecondBrainStack} from "../lib/stacks/second-brain-stack";
import {App} from "aws-cdk-lib";

const app = new App();

// Only specify region, account comes from deployer's credentials
const env: cdk.Environment = {
    region: 'us-west-2', // Bedrock is only available in select regions
};

new SecondBrainStack(app, 'SecondBrainStack', {env, description: 'Main infrastructure for Second Brain'});
app.synth()
