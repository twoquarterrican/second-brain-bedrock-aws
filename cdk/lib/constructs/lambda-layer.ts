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

    // Get packages directory from context
    const packagesDir = this.node.tryGetContext('PackagesDirectoryPath');
    if (!packagesDir || !fs.existsSync(packagesDir)) {
      throw new Error(
        `PackagesDirectoryPath context variable not set or invalid: ${packagesDir}`
      );
    }

    const lambdaDir = path.join(packagesDir, 'lambda');
    if (!fs.existsSync(lambdaDir)) {
      throw new Error(`Lambda directory not found at ${lambdaDir}`);
    }

    // Create layer with bundling
    this.layer = new lambda.LayerVersion(this, `${props.appName}-Layer`, {
      code: lambda.Code.fromAsset(lambdaDir, {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          volumes: [
            {
              hostPath: packagesDir,
              containerPath: '/packages',
            },
          ],
          command: [
            'bash',
            '-c',
            [
              // Create the proper layer structure
              'mkdir -p /asset-output/python',
              // Install uv package manager
              'pip install uv',
              // Install sb_shared in container environment so uv can resolve it as a dependency
              'pip install /packages/shared',
              // Install lambda package and all dependencies from pyproject.toml into the layer
              'cd /packages/lambda && uv pip install --target /asset-output/python .',
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
