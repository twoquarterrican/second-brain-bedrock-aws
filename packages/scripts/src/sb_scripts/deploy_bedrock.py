"""Deployment automation script for Second Brain Bedrock agent infrastructure."""

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from InquirerPy import inquirer

from ._deploy_utils import check_tools, run_command, show_install_instructions

load_dotenv()


class BedrockDeployer:
    """Handles deployment of Second Brain Bedrock agent infrastructure via CDK."""

    def __init__(self, region: str = None, require_approval: bool = True):
        """Initialize deployer.

        Args:
            region: AWS region for deployment
            require_approval: Whether to require approval before deployment
        """
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.require_approval = require_approval
        self.cdk_dir = Path(__file__).parent.parent / "cdk"
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

    def deploy_stack(self) -> bool:
        """Deploy Bedrock CDK stack to AWS."""
        cmd = ["cdk", "deploy", "BedrockStack", "--region", self.region]

        if not self.require_approval:
            cmd.append("--require-approval=never")

        result = run_command(
            cmd,
            cwd=self.cdk_dir,
            description="🚀 Deploying Bedrock infrastructure to AWS...",
        )
        return result.returncode == 0

    def run(self) -> bool:
        """Execute full deployment."""
        click.clear()
        click.secho("╔════════════════════════════════════════╗", fg="cyan")
        click.secho("║  Second Brain - Bedrock Deployment     ║", fg="cyan")
        click.secho("╚════════════════════════════════════════╝", fg="cyan")
        click.echo()

        click.echo(f"🌍 Region: {self.region}")
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

        # Show what will be deployed
        click.echo("3️⃣  Deployment summary:")
        click.echo("   Stack: BedrockStack")
        click.echo("   Resources:")
        click.echo("     - Bedrock Agent")
        click.echo("     - Lambda function (bedrock-agent-runtime)")
        click.echo("     - IAM roles and policies")
        click.echo()

        # Confirm deployment
        if self.require_approval:
            confirm = inquirer.confirm(
                message="Proceed with deployment?",
                default=False,
            ).execute()

            if not confirm:
                click.echo("Deployment cancelled.")
                return False

        click.echo()
        click.echo("4️⃣  Deploying...")
        if not self.deploy_stack():
            return False

        click.echo()
        click.secho("✨ Deployment complete!", fg="green")
        click.echo()
        click.echo("Next steps:")
        click.echo("  1. Check AWS Console for Bedrock Agent details")
        click.echo("  2. Verify the agent is working correctly")
        click.echo("  3. If deploying app after this, the processor Lambda")
        click.echo("     will automatically have invoke permissions set up")
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
def main(region: str, no_approval: bool):
    """Deploy Second Brain Bedrock agent infrastructure to AWS.

    This script will:
    1. Check for required tools (npm, aws, cdk)
    2. Install CDK dependencies
    3. Deploy the BedrockStack to your AWS account

    Make sure you're authenticated to AWS before running this.
    """
    deployer = BedrockDeployer(region=region, require_approval=not no_approval)

    if not deployer.run():
        sys.exit(1)


if __name__ == "__main__":
    main()
