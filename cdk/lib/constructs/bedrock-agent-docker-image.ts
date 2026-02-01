import * as cdk from 'aws-cdk-lib/core';
import {Construct} from 'constructs/lib/construct';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets'
import * as path from "node:path";

export interface Props {
    appName: string
}

export class BedrockAgentDockerImage extends Construct {
    readonly imageUri: string

    constructor(scope: Construct, id: string, props: Props) {
        super(scope, id);
        // deployment scripts will set this context for you automatically
        const dockerPath = this.node.tryGetContext("BedrockDockerfilePath");
        const projectRoot = this.node.tryGetContext("ProjectRootPath");
        const asset = new ecr_assets.DockerImageAsset(this, `${props.appName}-AppImage`, {
            directory: projectRoot,
            file: path.relative(projectRoot, dockerPath)
        });

        this.imageUri = asset.imageUri;
        new cdk.CfnOutput(this, 'ImageUri', {value: this.imageUri});
    }
}
