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
              // Install lambda dependencies from project (with workspace resolution)
              'cd /project && uv pip install --target /asset-output/python ./packages/lambda',
              // Remove the .pth file that points to non-existent editable install
              'rm -f /asset-output/python/sb_shared.pth',
              // Copy workspace source code directly into the layer
              'cp -r /project/packages/shared/src/sb_shared /asset-output/python/',
              'cp -r /project/packages/lambda/src/sb_lambda /asset-output/python/',
              // Remove dist-info directories for workspace packages (they\'re redundant with copied source)
              'rm -rf /asset-output/python/sb_shared-*.dist-info /asset-output/python/sb_lambda-*.dist-info',
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
