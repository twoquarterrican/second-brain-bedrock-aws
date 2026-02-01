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

    // Get project root from context to access workspace configuration
    const projectRoot = this.node.tryGetContext('ProjectRootPath');
    if (!projectRoot || !fs.existsSync(projectRoot)) {
      throw new Error(
        `ProjectRootPath context variable not set or invalid: ${projectRoot}`
      );
    }

    const lambdaDir = path.join(projectRoot, 'packages', 'lambda');
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
              hostPath: projectRoot,
              containerPath: '/project',
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
              // Install lambda package and all dependencies from pyproject.toml into the layer
              // Run from project root so uv sees the workspace configuration
              'cd /project && uv pip install --target /asset-output/python ./packages/lambda',
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
