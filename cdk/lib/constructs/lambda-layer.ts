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
              // Create the proper layer structure for AWS Lambda
              'mkdir -p /asset-output/python',
              // Install uv package manager
              'pip install uv',
              // Install dependencies using AWS Lambda best practices
              // Using --target with Lambda-optimized flags
              // See: https://docs.astral.sh/uv/guides/integration/aws-lambda/
              'cd /project && uv pip install ' +
              '--target /asset-output/python ' +
              '--no-installer-metadata ' +
              '--no-compile-bytecode ' +
              '--python-platform x86_64-manylinux2014 ' +
              '--python 3.13 ' +
              './packages/shared ./packages/lambda',
              // Remove .pth files that point to workspace editable installs
              'rm -f /asset-output/python/*.pth',
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
