import * as cdk from 'aws-cdk-lib/core';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as fs from 'node:fs';
import * as path from 'path';
import { Construct } from 'constructs';

export interface Props {
  appName: string;
}

export class LambdaLayer extends Construct {
  readonly layer: lambda.LayerVersion;

  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id);

    // Get lambda directory from context
    const lambdaDir = this.node.tryGetContext('LambdaDirectoryPath');
    if (!lambdaDir || !fs.existsSync(lambdaDir)) {
      throw new Error(
        `LambdaDirectoryPath context variable not set or invalid: ${lambdaDir}`
      );
    }

    // Get shared package directory
    const projectRoot = path.dirname(path.dirname(path.dirname(lambdaDir)));
    const sharedDir = path.join(projectRoot, 'packages', 'shared');

    if (!fs.existsSync(sharedDir)) {
      throw new Error(`Shared package directory not found: ${sharedDir}`);
    }

    // Create layer with bundling
    this.layer = new lambda.LayerVersion(this, `${props.appName}-Layer`, {
      code: lambda.Code.fromAsset(lambdaDir, {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash',
            '-c',
            [
              // Create the proper layer structure
              'mkdir -p /asset-output/python',
              // Install dependencies from lambda pyproject.toml
              `cd ${lambdaDir} && pip install . --target /asset-output/python --no-deps`,
              // Install external dependencies
              `pip install boto3 pydantic aws-lambda-logging requests --target /asset-output/python`,
              // Copy editable dependencies (sb_shared)
              `cp -r ${sharedDir}/src/sb_shared /asset-output/python/`,
            ].join(' && '),
          ],
          user: 'root',
        },
      }),
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      description: `Dependencies and shared libraries for ${props.appName}`,
    });
  }
}
