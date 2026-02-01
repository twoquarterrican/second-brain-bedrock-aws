"""
Telegram Webhook Setup Script

Interactive CLI tool to configure your Telegram bot webhook for Second Brain.
This script helps you:
1. Validate your Telegram bot token
2. Retrieve your Lambda Function URL from CDK stack
3. Set up the webhook on Telegram servers
4. Verify the configuration works

Run with: uv run setup-telegram
"""

import os
import sys
from pathlib import Path
from typing import Optional

import boto3
import click
import requests
from InquirerPy import inquirer

# Telegram Bot API endpoint
TELEGRAM_API = "https://api.telegram.org"


def load_env_file(env_path: Optional[str] = None) -> dict:
    """Load environment variables from .env file or environment."""
    env_vars = {}

    if env_path is None:
        env_path = Path(".env")
    else:
        env_path = Path(env_path)

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip().strip("'\"")

    # Override with actual environment variables
    env_vars.update(os.environ)
    return env_vars


def get_telegram_bot_info(bot_token: str) -> dict:
    """Get bot info from Telegram API to validate token."""
    try:
        response = requests.get(f"{TELEGRAM_API}/bot{bot_token}/getMe", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        click.secho(f"✗ Failed to validate Telegram bot token: {e}", fg="red")
        return None


def get_cdk_outputs() -> Optional[dict]:
    """Retrieve CDK stack outputs from CloudFormation."""
    try:
        cfn = boto3.client("cloudformation")
        response = cfn.describe_stacks(StackName="ApplicationStack")
        stacks = response.get("Stacks", [])

        if not stacks:
            return None

        stack = stacks[0]
        outputs = {}

        for output in stack.get("Outputs", []):
            outputs[output["OutputKey"]] = output["OutputValue"]

        return outputs
    except Exception as e:
        click.secho(f"! Could not retrieve CDK stack outputs: {e}", fg="yellow")
        return None


def set_telegram_webhook(bot_token: str, webhook_url: str) -> bool:
    """Set webhook on Telegram bot."""
    try:
        response = requests.post(
            f"{TELEGRAM_API}/bot{bot_token}/setWebhook",
            json={"url": webhook_url},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("ok"):
            return True
        else:
            click.secho(f"✗ Telegram error: {result.get('description')}", fg="red")
            return False
    except requests.exceptions.RequestException as e:
        click.secho(f"✗ Failed to set webhook: {e}", fg="red")
        return False


def get_telegram_webhook_info(bot_token: str) -> Optional[dict]:
    """Get current webhook info from Telegram."""
    try:
        response = requests.get(f"{TELEGRAM_API}/bot{bot_token}/getWebhookInfo", timeout=5)
        response.raise_for_status()
        result = response.json()

        if result.get("ok"):
            return result.get("result")
        return None
    except requests.exceptions.RequestException:
        return None


def validate_url(url: str) -> bool:
    """Validate webhook URL format."""
    if not url.startswith("https://"):
        return False
    if not len(url) > 10:
        return False
    return True


@click.command()
@click.option(
    "--bot-token",
    envvar="TELEGRAM_BOT_TOKEN",
    default=None,
    help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)",
)
@click.option(
    "--webhook-url",
    default=None,
    help="Lambda Function URL for webhook (retrieved from CDK if not provided)",
)
@click.option(
    "--env-file",
    type=click.Path(exists=False),
    default=".env",
    help="Path to .env file",
)
@click.option(
    "--region",
    envvar="AWS_REGION",
    default="us-west-2",
    help="AWS region for CloudFormation lookup (Bedrock requires us-west-2)",
)
def main(bot_token: str, webhook_url: str, env_file: str, region: str):
    """
    Interactive setup for Telegram webhook on Second Brain.

    This tool guides you through configuring your Telegram bot to send
    messages to your Second Brain Lambda function.
    """
    click.clear()
    click.secho("╔════════════════════════════════════════╗", fg="cyan")
    click.secho("║    Second Brain - Telegram Setup       ║", fg="cyan")
    click.secho("╚════════════════════════════════════════╝", fg="cyan")
    click.echo()

    # Set AWS region for boto3
    if region:
        os.environ["AWS_REGION"] = region

    # Load environment variables
    load_env_file(env_file)

    # 1. Get Telegram Bot Token
    click.echo("📱 Step 1: Telegram Bot Token")
    click.echo("   You'll need a bot token from @BotFather on Telegram.")
    click.echo("   Learn more: https://core.telegram.org/bots#botfather")
    click.echo()

    if not bot_token:
        bot_token = inquirer.secret(
            message="Enter your Telegram bot token:",
            instruction="(hidden input)",
        ).execute()

    if not bot_token:
        click.secho("✗ Bot token is required", fg="red")
        sys.exit(1)

    # Validate token
    click.echo("   Validating bot token...", nl=False)
    bot_info = get_telegram_bot_info(bot_token)

    if not bot_info:
        sys.exit(1)

    bot_name = bot_info.get("result", {}).get("username", "Unknown")
    click.secho(f" ✓ Token valid (@{bot_name})", fg="green")
    click.echo()

    # 2. Get Lambda Function URL
    click.echo("🔗 Step 2: Lambda Function URL")
    click.echo("   This is the HTTPS endpoint for your webhook.")
    click.echo()

    if not webhook_url:
        # Try to get from CDK outputs
        click.echo("   Looking up CDK stack outputs...", nl=False)
        outputs = get_cdk_outputs()

        if outputs and "LambdaFunctionUrl" in outputs:
            webhook_url = outputs["LambdaFunctionUrl"]
            click.secho(" ✓ Found", fg="green")
            click.echo(f"   From CDK: {webhook_url}")
            click.echo()

            # Ask if they want to use it
            use_cdk_url = inquirer.confirm(
                message="Use this Lambda Function URL?",
                default=True,
            ).execute()

            if not use_cdk_url:
                webhook_url = None
        else:
            click.secho(" ! Not found", fg="yellow")
            click.echo()

    if not webhook_url:
        webhook_url = inquirer.text(
            message="Enter Lambda Function URL:",
            instruction="Must start with https://",
            validate=lambda x: validate_url(x),
            invalid_message="Must be a valid HTTPS URL",
        ).execute()

    if not validate_url(webhook_url):
        click.secho("✗ Invalid webhook URL", fg="red")
        sys.exit(1)

    click.echo()

    # 3. Summary and confirmation
    click.echo("📋 Step 3: Review Configuration")
    click.echo()
    click.echo(f"  Bot:     @{bot_name}")
    click.echo(f"  Webhook: {webhook_url}")
    click.echo()

    confirm = inquirer.confirm(
        message="Proceed with webhook setup?",
        default=True,
    ).execute()

    if not confirm:
        click.echo("Setup cancelled.")
        sys.exit(0)

    # 4. Set webhook
    click.echo()
    click.echo("⚙️  Step 4: Setting Up Webhook")
    click.echo("   Configuring Telegram bot...", nl=False)

    if set_telegram_webhook(bot_token, webhook_url):
        click.secho(" ✓ Webhook configured", fg="green")
    else:
        sys.exit(1)

    # 5. Verify webhook
    click.echo("   Verifying webhook...", nl=False)
    webhook_info = get_telegram_webhook_info(bot_token)

    if webhook_info:
        url = webhook_info.get("url", "")
        if url == webhook_url:
            click.secho(" ✓ Verified", fg="green")
            click.echo()
            click.echo("   Webhook info:")
            click.echo(f"     URL: {url}")
            click.echo(f"     Pending updates: {webhook_info.get('pending_update_count', 0)}")

            if webhook_info.get("last_error_date"):
                click.secho(
                    f"     Last error: {webhook_info.get('last_error_message')}",
                    fg="yellow",
                )
        else:
            click.secho(" ✗ URL mismatch", fg="red")
            sys.exit(1)
    else:
        click.secho(" ! Could not verify", fg="yellow")

    click.echo()
    click.echo("✨ Setup Complete!")
    click.echo()
    click.echo("Next steps:")
    click.echo("  1. Send a message to your bot on Telegram")
    click.echo("  2. Check CloudWatch Logs to see the message processed")
    click.echo("  3. View your tasks, todos, and reminders")
    click.echo()
    click.secho("📚 Documentation: https://github.com/yourusername/second-brain", fg="cyan")
    click.echo()


if __name__ == "__main__":
    main()
