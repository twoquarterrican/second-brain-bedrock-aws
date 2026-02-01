import * as cdk from 'aws-cdk-lib/core';
import {Construct} from 'constructs/lib/construct';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets'
import * as path from 'path';
import * as fs from "node:fs";

export interface Props {
    appName: string
}

export class BedrockAgentDockerImage extends Construct {
    readonly imageUri: string

    constructor(scope: Construct, id: string, props: Props) {
        super(scope, id);
        // deployment scripts will set this context for you automatically
        const directory = this.node.tryGetContext("BedrockDockerfileParentPath");
        if (!directory || !fs.existsSync(directory)) {
            throw new Error("BedrockDockerfileParentPath");
        }
        const asset = new ecr_assets.DockerImageAsset(this, `${props.appName}-AppImage`, {
            directory: path.join(__dirname, "../../../"), // path to root of the project
        });

        this.imageUri = asset.imageUri;
        new cdk.CfnOutput(this, 'ImageUri', {value: this.imageUri});
    }
}
