import * as cdk from 'aws-cdk-lib/core';
import {IConstruct} from 'constructs/lib/construct';
import {SecondBrainStorage} from "../constructs/second-brain-storage";
import {BedrockAgentDockerImage} from "../constructs/bedrock-agent-docker-image";
import {SecondBrainApp} from "../constructs/second-brain-app";
import {AgentCore} from "../constructs/agent-core";

export class SecondBrainStack extends cdk.Stack {
    public constructor(scope: IConstruct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);
        const appName = 'second-brain';

        // 1. Create shared storage (no dependencies)
        const storageStack = new SecondBrainStorage(this, `Storage`);

        const dockerImageStack = new BedrockAgentDockerImage(this, `DockerImage`, {
            appName,
        });
        const agentCore = new AgentCore(this, `AgentCore`, {
            appName,
            imageUri: dockerImageStack.imageUri,
        });

        // 3. Create application infrastructure (depends on storage and bedrock runtime)
        new SecondBrainApp(this, 'SecondBrainApp', {
            dataTable: storageStack.dataTable,
            dataBucket: storageStack.dataBucket,
            agentCoreRuntimeArn: agentCore.runtimeId,
        });
    }
}
