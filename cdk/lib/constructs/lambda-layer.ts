import * as cdk from 'aws-cdk-lib/core';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as fs from 'node:fs';
import * as path from 'path';
import * as crypto from 'node:crypto';
import { Construct } from 'constructs';

export interface Props {
  appName: string;
}

/**
 * Compute a hash of all Python source files in lambda and shared packages.
 * Used to invalidate the layer cache whenever code changes.
 */
function computeSourceHash(projectRoot: string): string {
  const files: string[] = [];

  // Collect all Python files from shared and lambda packages
  const packagesToHash = ['packages/shared/src/sb_shared', 'packages/lambda/src/sb_lambda'];

  for (const pkgPath of packagesToHash) {
    const fullPath = path.join(projectRoot, pkgPath);
    if (fs.existsSync(fullPath)) {
      collectFiles(fullPath, files);
    }
  }

  // Sort for consistent ordering
  files.sort();

  // Compute hash of all file contents
  const hash = crypto.createHash('sha256');
  for (const file of files) {
    const content = fs.readFileSync(file, 'utf8');
    hash.update(content);
  }

  return hash.digest('hex').slice(0, 16);
}

/**
 * Recursively collect all .py files from a directory.
 */
function collectFiles(dir: string, files: string[]): void {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      collectFiles(fullPath, files);
    } else if (entry.name.endsWith('.py')) {
      files.push(fullPath);
    }
  }
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

    // Compute hash of all source files to invalidate cache on code changes
    const sourceHash = computeSourceHash(projectRoot);

    // Create layer with bundling
    this.layer = new lambda.LayerVersion(this, `${props.appName}-Layer`, {
      code: lambda.Code.fromAsset(lambdaDir, {
        assetHash: sourceHash,
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
              // Remove .pth files and dist-info that point to workspace editable installs
              'rm -f /asset-output/python/*.pth',
              'rm -rf /asset-output/python/sb_shared-*.dist-info /asset-output/python/sb_lambda-*.dist-info',
              // Copy workspace source code directly (workspace packages are not fully installed)
              'cp -r /project/packages/shared/src/sb_shared /asset-output/python/',
              'cp -r /project/packages/lambda/src/sb_lambda /asset-output/python/',
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
