import * as cdk from 'aws-cdk-lib';
import * as fs from 'node:fs';
import * as path from 'node:path';
import {SecondBrainStack} from "../lib/stacks/second-brain-stack";
import {App} from "aws-cdk-lib";
import * as dotenv from 'dotenv';

const app = new App();

// Discover project root by walking up directory tree
function findProjectRoot(current: string): string {
  while (current !== path.dirname(current)) {
    if (fs.existsSync(path.join(current, '.git')) ||
        (fs.existsSync(path.join(current, 'pyproject.toml')) &&
         fs.existsSync(path.join(current, 'packages')))) {
      return current;
    }
    current = path.dirname(current);
  }
  throw new Error('Could not find project root');
}

const projectRoot = findProjectRoot(path.dirname(__filename));
const bedrockDir = path.join(projectRoot, 'packages', 'bedrock');
const packagesDir = path.join(projectRoot, 'packages');

// Set context variables for constructs to use
app.node.setContext('ProjectRootPath', projectRoot);
app.node.setContext('BedrockDockerfilePath', path.join(bedrockDir , 'Dockerfile'));
app.node.setContext('PackagesDirectoryPath', packagesDir);

// Load environment variables from .env and .env.local
dotenv.config({ path: path.join(projectRoot, '.env') });
dotenv.config({ path: path.join(projectRoot, '.env.local'), override: true });

// CDK needs both account and region. Account comes from CDK_DEFAULT_ACCOUNT env var
// which is set by the AWS SDK/CLI based on the current AWS credentials
const env: cdk.Environment = {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: 'us-west-2', // Bedrock is only available in select regions
};

new SecondBrainStack(app, 'SecondBrainStack', {env, description: 'Main infrastructure for Second Brain'});
app.synth()
