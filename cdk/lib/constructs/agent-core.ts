import * as cdk from 'aws-cdk-lib/core';
import {Construct} from 'constructs/lib/construct';
import * as bedrockagentcore from 'aws-cdk-lib/aws-bedrockagentcore';
import * as iam from 'aws-cdk-lib/aws-iam';

export interface Props {
    imageUri: string
    appName: string
}

export class AgentCore extends Construct {
    readonly agentCoreRuntime: bedrockagentcore.CfnRuntime;
    readonly agentCoreMemory: bedrockagentcore.CfnMemory;
    readonly runtimeId: string;
    readonly runtimeAlias: string;

    constructor(scope: Construct, id: string, props: Props) {
        super(scope, id);

        const region = cdk.Stack.of(this).region;
        const accountId = cdk.Stack.of(this).account;

        new iam.Role(this, `${props.appName}-AgentCoreGatewayRole`, {
            assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com'),
            description: 'IAM role for Bedrock AgentCore Runtime',
        });

        this.agentCoreMemory = new bedrockagentcore.CfnMemory(this, `${props.appName}-AgentCoreMemory`, {
            name: "second_brain_agent_memory",
            eventExpiryDuration: 30,
            description: "Memory resource with 30 days event expiry",
            memoryStrategies: [
                {
                    userPreferenceMemoryStrategy: {
                        name: "UserPreferences",
                        namespaces: ["/users/{actorId}/preferences"],
                        description: "Instance of built-in user preference memory strategy"
                    }
                },
                {
                    semanticMemoryStrategy: {
                        name: "SemanticFacts",
                        namespaces: ["/users/{actorId}/facts"],
                        description: "Instance of built-in semantic memory strategy"
                    }
                },
                {
                    summaryMemoryStrategy: {
                        name: "SessionSummaries",
                        namespaces: ["/summaries/{actorId}/{sessionId}"],
                        description: "Instance of built-in summary memory strategy"
                    }
                }
            ],
        });

        // taken from https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-execution
        const runtimePolicy = new iam.PolicyDocument({
            statements: [
                new iam.PolicyStatement({
                    sid: 'ECRImageAccess',
                    effect: iam.Effect.ALLOW,
                    actions: ['ecr:BatchGetImage', 'ecr:GetDownloadUrlForLayer'],
                    resources: [
                        `arn:aws:ecr:${region}:${accountId}:repository/*`,
                    ],
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['logs:DescribeLogStreams', 'logs:CreateLogGroup'],
                    resources: [
                        `arn:aws:logs:${region}:${accountId}:log-group:/aws/bedrock-agentcore/runtimes/*`,
                    ],
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['logs:DescribeLogGroups'],
                    resources: [
                        `arn:aws:logs:${region}:${accountId}:log-group:*`,
                    ],
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['logs:CreateLogStream', 'logs:PutLogEvents'],
                    resources: [
                        `arn:aws:logs:${region}:${accountId}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*`,
                    ],
                }),
                new iam.PolicyStatement({
                    sid: 'ECRTokenAccess',
                    effect: iam.Effect.ALLOW,
                    actions: ['ecr:GetAuthorizationToken'],
                    resources: ['*'],
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: [
                        'xray:PutTraceSegments',
                        'xray:PutTelemetryRecords',
                        'xray:GetSamplingRules',
                        'xray:GetSamplingTargets',
                    ],
                    resources: ['*'],
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['cloudwatch:PutMetricData'],
                    resources: ['*'],
                    conditions: {
                        StringEquals: {'cloudwatch:namespace': 'bedrock-agentcore'},
                    },
                }),
                new iam.PolicyStatement({
                    sid: 'GetAgentAccessToken',
                    effect: iam.Effect.ALLOW,
                    actions: [
                        'bedrock-agentcore:GetWorkloadAccessToken',
                        'bedrock-agentcore:GetWorkloadAccessTokenForJWT',
                        'bedrock-agentcore:GetWorkloadAccessTokenForUserId',
                    ],
                    resources: [
                        `arn:aws:bedrock-agentcore:${region}:${accountId}:workload-identity-directory/default`,
                        `arn:aws:bedrock-agentcore:${region}:${accountId}:workload-identity-directory/default/workload-identity/agentName-*`,
                    ],
                }),
                new iam.PolicyStatement({
                    sid: 'BedrockModelInvocation',
                    effect: iam.Effect.ALLOW,
                    actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
                    resources: [
                        `arn:aws:bedrock:*::foundation-model/*`,
                        `arn:aws:bedrock:${region}:${accountId}:*`,
                    ],
                }),
                new iam.PolicyStatement({
                    sid: 'AgentCoreMemoryAccess',
                    effect: iam.Effect.ALLOW,
                    actions: [
                        'bedrock-agentcore:CreateEvent',
                        'bedrock-agentcore:ListEvents',
                        'bedrock-agentcore:SaveEvent',
                        'bedrock-agentcore:PutMemory',
                        'bedrock-agentcore:GetMemory',
                        'bedrock-agentcore:DeleteMemory',
                        'bedrock-agentcore:QueryMemory',
                    ],
                    resources: [
                        `arn:aws:bedrock-agentcore:${region}:${accountId}:memory/*`,
                    ],
                }),
            ],
        });

        const runtimeRole = new iam.Role(this, `${props.appName}-AgentCoreRuntimeRole`, {
            assumedBy: new iam.ServicePrincipal('bedrock-agentcore.amazonaws.com'),
            description: 'IAM role for Bedrock AgentCore Runtime',
            inlinePolicies: {
                RuntimeAccessPolicy: runtimePolicy
            }
        });

        this.agentCoreRuntime = new bedrockagentcore.CfnRuntime(this, `${props.appName}-AgentCoreRuntime`, {
            agentRuntimeArtifact: {
                containerConfiguration: {
                    containerUri: props.imageUri
                }
            },
            agentRuntimeName: "second_brain_agent",
            protocolConfiguration: "HTTP",
            networkConfiguration: {
                networkMode: "PUBLIC"
            },
            roleArn: runtimeRole.roleArn,
            environmentVariables: {
                "AWS_REGION": region,
                "BEDROCK_AGENTCORE_MEMORY_ID": this.agentCoreMemory.attrMemoryId,
            }
        });

        // Export runtime ID and alias for use by other stacks
        // The runtime name is used as the agent ID for invoke_agent API
        // ASIS is the standard alias for as-is execution
        this.runtimeId = this.agentCoreRuntime.attrRuntimeArn;
        this.runtimeAlias = 'ASIS';

        new cdk.CfnOutput(this, 'RuntimeArn', {
            value: this.runtimeId,
            exportName: 'SecondBrainAgentCoreRuntimeArn',
            description: 'ARN of the Bedrock AgentCore runtime',
        });
    }
}
