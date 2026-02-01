"""Unified CDK deployment script for Second Brain infrastructure."""

import os
import sys

import click
from dotenv import load_dotenv
from InquirerPy import inquirer

from ._deploy_utils import check_tools, run_command, show_install_instructions
from .cdk_utils import find_bedrock_dockerfile_parent, find_project_root

load_dotenv()


class SecondBrainDeployer:
    """Handles unified CDK deployment for Second Brain."""

    def __init__(self, region: str = None, require_approval: bool = True):
        """Initialize deployer.

        Args:
            region: AWS region for deployment
            require_approval: Whether to require approval before deployment
        """
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.require_approval = require_approval
        self.project_root = find_project_root()
        self.cdk_dir = self.project_root / "cdk"
        self.bedrock_docker_path = find_bedrock_dockerfile_parent()

        self.tools_info = {
            "npm": "https://nodejs.org",
            "aws": "pip install awscli",
            "cdk": "npm install -g aws-cdk",
        }

    def check_prerequisites(self) -> bool:
        """Check if required tools are installed."""
        if not check_tools(list(self.tools_info.keys())):
            show_install_instructions(self.tools_info)
            return False
        return True

    def install_dependencies(self) -> bool:
        """Install CDK dependencies."""
        result = run_command(
            ["npm", "install"],
            cwd=self.cdk_dir,
            capture_output=True,
            description="📦 Installing CDK dependencies...",
        )
        return result.returncode == 0

    def synth_stack(self) -> bool:
        """Synthesize CDK stack to CloudFormation template."""
        cmd = [
            "cdk",
            "synth",
            "--region",
            self.region,
            "--context",
            f"BedrockDockerfileParentPath={self.bedrock_docker_path.as_posix()}",
        ]

        result = run_command(
            cmd,
            cwd=self.cdk_dir,
            description="🔨 Synthesizing CloudFormation template...",
        )
        return result.returncode == 0

    def deploy_stack(self) -> bool:
        """Deploy CDK stack to AWS."""
        cmd = [
            "cdk",
            "deploy",
            "--region",
            self.region,
            "--context",
            f"BedrockDockerfileParentPath={self.bedrock_docker_path.as_posix()}",
        ]

        if not self.require_approval:
            cmd.append("--require-approval=never")

        result = run_command(
            cmd,
            cwd=self.cdk_dir,
            description="🚀 Deploying Second Brain to AWS...",
        )
        return result.returncode == 0

    def run(self, synth_only: bool = False) -> bool:
        """Execute deployment or synthesis.

        Args:
            synth_only: If True, only synthesize CloudFormation template
        """
        click.clear()
        title = "CDK Synthesis" if synth_only else "CDK Deployment"
        click.secho("╔════════════════════════════════════════╗", fg="cyan")
        click.secho(f"║  Second Brain - {title:<22} ║", fg="cyan")
        click.secho("╚════════════════════════════════════════╝", fg="cyan")
        click.echo()

        click.echo(f"🌍 Region: {self.region}")
        click.echo(f"📁 Project: {self.project_root}")
        click.echo(f"🐳 Bedrock Dockerfile: {self.bedrock_docker_path}")
        click.echo()

        # Check prerequisites
        click.echo("1️⃣  Checking prerequisites...")
        if not self.check_prerequisites():
            return False
        click.secho("   ✓ All required tools found", fg="green")
        click.echo()

        # Install dependencies
        click.echo("2️⃣  Setting up CDK project...")
        if not self.install_dependencies():
            return False
        click.echo()

        # Show what will be processed
        click.echo("3️⃣  Stack summary:")
        click.echo("   Stack: SecondBrainStack")
        click.echo("   Resources:")
        click.echo("     Storage:")
        click.echo("       - DynamoDB table (second-brain)")
        click.echo("       - S3 bucket (second-brain-data)")
        click.echo("     Bedrock Agent:")
        click.echo("       - Docker image from: " + str(self.bedrock_docker_path))
        click.echo("       - Lambda function (bedrock-agent-runtime)")
        click.echo("     Application:")
        click.echo("       - SQS queue (second-brain-messages)")
        click.echo("       - Lambda functions (message-handler, processor)")
        click.echo()

        # Confirm if deploying (not for synth-only)
        if not synth_only and self.require_approval:
            confirm = inquirer.confirm(
                message="Proceed with deployment?",
                default=False,
            ).execute()

            if not confirm:
                click.echo("Operation cancelled.")
                return False

        click.echo()
        step_num = "4️⃣"
        if synth_only:
            click.echo(f"{step_num}  Synthesizing...")
            if not self.synth_stack():
                return False
            click.echo()
            click.secho("✨ Synthesis complete!", fg="green")
            click.echo()
            click.echo("CloudFormation template generated to: cdk.out/")
        else:
            click.echo(f"{step_num}  Deploying...")
            if not self.deploy_stack():
                return False
            click.echo()
            click.secho("✨ Deployment complete!", fg="green")
            click.echo()
            click.echo("Next steps:")
            click.echo("  1. Check AWS Console for stack details")
            click.echo("  2. Configure Telegram webhook: uv run setup-telegram")
            click.echo("  3. Send a test message to your bot")

        click.echo()
        click.secho("📚 Docs: https://github.com/yourusername/second-brain", fg="cyan")
        click.echo()

        return True


@click.command()
@click.option(
    "--region",
    envvar="AWS_REGION",
    default="us-west-2",
    help="AWS region for deployment (Bedrock requires us-west-2)",
)
@click.option(
    "--no-approval",
    is_flag=True,
    help="Skip approval confirmation",
)
@click.option(
    "--synth-only",
    is_flag=True,
    help="Only synthesize CloudFormation template, don't deploy",
)
def main(region: str, no_approval: bool, synth_only: bool):
    """Deploy or synthesize Second Brain infrastructure.

    This script will:
    1. Check for required tools (npm, aws, cdk)
    2. Install CDK dependencies
    3. Synthesize or deploy SecondBrainStack with all resources

    Make sure you're authenticated to AWS before running deploy.
    """
    deployer = SecondBrainDeployer(region=region, require_approval=not no_approval)

    if not deployer.run(synth_only=synth_only):
        sys.exit(1)


if __name__ == "__main__":
    main()
