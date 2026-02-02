"""
Telegram Bot Configuration Script

Interactive CLI tool to configure your Telegram bot webhook for Second Brain.
Supports multiple commands:
- telegram setup_webhook: Set up webhook on Telegram servers
- telegram show_webhook: Display current webhook configuration

Environment Variables:
- TELEGRAM_BOT_TOKEN: Your Telegram bot token (from @BotFather)
- TELEGRAM_SECRET_TOKEN: Secret token for webhook security (set in .env.local)

Run with: uv run telegram <command>
"""

import sys
from typing import Optional

import boto3
import click
import requests
from InquirerPy import inquirer
from sb_scripts.utils import load_env

# Telegram Bot API endpoint
TELEGRAM_API = "https://api.telegram.org"


def get_telegram_bot_info(bot_token: str) -> dict:
    """Get bot info from Telegram API to validate token."""
    try:
        response = requests.get(f"{TELEGRAM_API}/bot{bot_token}/getMe", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        click.secho(f"✗ Failed to validate Telegram bot token: {e}", fg="red")
        return None


def get_webhook_url_from_stack() -> tuple[Optional[str], Optional[str]]:
    """
    Retrieve webhook URL from CDK stack outputs.

    Looks for an output with ExportName 'SecondBrainWebhookUrl'.

    Returns:
        Tuple of (webhook_url, error_message). One will be None.
    """
    try:
        cfn = boto3.client("cloudformation")
        response = cfn.describe_stacks(StackName="SecondBrainStack")
        stacks = response.get("Stacks", [])

        if not stacks:
            return None, "No CloudFormation stacks found with name 'SecondBrainStack'"

        stack = stacks[0]

        # Look for output with ExportName 'SecondBrainWebhookUrl'
        for output in stack.get("Outputs", []):
            if output.get("ExportName") == "SecondBrainWebhookUrl":
                webhook_url = output.get("OutputValue")
                if webhook_url:
                    return webhook_url, None

        return (
            None,
            "Stack found but webhook URL output not found (looking for ExportName 'SecondBrainWebhookUrl')",
        )

    except boto3.exceptions.Boto3Error as e:
        return None, f"AWS API error: {e}"
    except Exception as e:
        return None, f"Failed to retrieve stack outputs: {e}"


def set_telegram_webhook(bot_token: str, webhook_url: str, secret_token: str) -> bool:
    """
    Set webhook on Telegram bot with secret token.

    Args:
        bot_token: Telegram bot token
        webhook_url: HTTPS URL for webhook
        secret_token: Secret token for webhook security

    Returns:
        True if successful
    """
    try:
        response = requests.post(
            f"{TELEGRAM_API}/bot{bot_token}/setWebhook",
            json={"url": webhook_url, "secret_token": secret_token},
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


@click.group()
def cli():
    """Telegram bot configuration for Second Brain."""
    # Load environment variables from .env and .env.local
    load_env()


@cli.command()
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
    "--secret-token",
    envvar="TELEGRAM_SECRET_TOKEN",
    default=None,
    help="Secret token for webhook security (or set TELEGRAM_SECRET_TOKEN env var)",
)
@click.option(
    "--env-file",
    type=click.Path(exists=False),
    default=".env",
    help="Path to .env file with AWS credentials/config",
)
def setup_webhook(bot_token: str, webhook_url: str, secret_token: str, env_file: str):
    """
    Set up Telegram webhook for Second Brain.

    This command guides you through configuring your Telegram bot to send
    messages to your Second Brain Lambda function with secure secret token verification.
    """
    click.clear()
    click.secho("╔════════════════════════════════════════╗", fg="cyan")
    click.secho("║  Second Brain - Telegram Webhook Setup ║", fg="cyan")
    click.secho("╚════════════════════════════════════════╝", fg="cyan")
    click.echo()

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
        # Try to get from CDK stack outputs
        click.echo("   Retrieving webhook URL from CloudFormation stack...", nl=False)
        webhook_url, error = get_webhook_url_from_stack()

        if webhook_url:
            click.secho(" ✓ Found", fg="green")
            click.echo(f"   From stack: {webhook_url}")
            click.echo()

            # Ask if they want to use it
            use_stack_url = inquirer.confirm(
                message="Use this Lambda Function URL?",
                default=True,
            ).execute()

            if not use_stack_url:
                webhook_url = None
        else:
            click.secho(" ✗ Failed", fg="red")
            click.echo()
            click.echo(f"   Problem: {error}")
            click.echo()
            click.echo("   To fix this, ensure:")
            click.echo("   • Your CloudFormation stack 'SecondBrainStack' is deployed")
            click.echo(
                "   • AWS credentials are configured (AWS_PROFILE env var, ~/.aws/credentials, etc.)"
            )
            click.echo("   • AWS_REGION is set to the correct region")
            click.echo()
            choice = inquirer.select(
                message="What would you like to do?",
                choices=["Enter URL manually", "Quit and fix permissions"],
                default="Enter URL manually",
            ).execute()

            if choice == "Quit and fix permissions":
                click.echo("Please configure AWS credentials and try again.")
                click.echo("Set AWS_PROFILE and AWS_REGION in your .env file or environment.")
                sys.exit(1)

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

    # 3. Get Secret Token
    click.echo("🔐 Step 3: Webhook Secret Token")
    click.echo("   Secret token is used to verify webhook requests are from Telegram.")
    click.echo()

    if secret_token:
        click.echo("   Found TELEGRAM_SECRET_TOKEN in environment:")
        click.echo(f"   ••••••••••••{secret_token[-8:]}")
        click.echo()

        use_env_token = inquirer.confirm(
            message="Use this secret token?",
            default=True,
        ).execute()

        if not use_env_token:
            secret_token = None
    else:
        click.secho(
            "   ⚠ TELEGRAM_SECRET_TOKEN not found in environment",
            fg="yellow",
        )

    if not secret_token:
        secret_token = inquirer.text(
            message="Enter webhook secret token (or press Enter to generate one):",
            default="",
        ).execute()

        if not secret_token:
            # Generate a secure token
            import secrets

            secret_token = secrets.token_urlsafe(32)
            click.echo(f"   Generated token: {secret_token}")
            click.echo("   ⚠ Save this to TELEGRAM_SECRET_TOKEN in your .env.local file!")

    click.echo()

    # 4. Summary and confirmation
    click.echo("📋 Step 4: Review Configuration")
    click.echo()
    click.echo(f"  Bot:           @{bot_name}")
    click.echo(f"  Webhook URL:   {webhook_url}")
    click.echo(f"  Secret Token:  ••••••••••••{secret_token[-8:]}")
    click.echo()

    confirm = inquirer.confirm(
        message="Proceed with webhook setup?",
        default=True,
    ).execute()

    if not confirm:
        click.echo("Setup cancelled.")
        sys.exit(0)

    # 5. Set webhook
    click.echo()
    click.echo("⚙️  Step 5: Setting Up Webhook")
    click.echo("   Configuring Telegram bot...", nl=False)

    if set_telegram_webhook(bot_token, webhook_url, secret_token):
        click.secho(" ✓ Webhook configured", fg="green")
    else:
        sys.exit(1)

    # 6. Verify webhook
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
    click.echo("  1. Save secret token to .env.local:")
    click.echo(f"     TELEGRAM_SECRET_TOKEN={secret_token}")
    click.echo("  2. Send a message to your bot on Telegram")
    click.echo("  3. Check CloudWatch Logs to see the message processed")
    click.echo("  4. View your tasks, todos, and reminders")
    click.echo()
    click.secho(
        "📚 Documentation: https://github.com/yourusername/second-brain",
        fg="cyan",
    )
    click.echo()


@cli.command()
@click.option(
    "--bot-token",
    envvar="TELEGRAM_BOT_TOKEN",
    default=None,
    help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)",
)
def show_webhook(bot_token: str):
    """
    Show current webhook configuration from Telegram.

    Displays the URL, secret token hash, and error information if any.
    """
    click.clear()
    click.secho("╔════════════════════════════════════════╗", fg="cyan")
    click.secho("║ Second Brain - Telegram Webhook Status ║", fg="cyan")
    click.secho("╚════════════════════════════════════════╝", fg="cyan")
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
    click.echo("Validating bot token...", nl=False)
    bot_info = get_telegram_bot_info(bot_token)

    if not bot_info:
        sys.exit(1)

    bot_name = bot_info.get("result", {}).get("username", "Unknown")
    click.secho(f" ✓ Valid (@{bot_name})", fg="green")
    click.echo()

    # Get webhook info
    click.echo("Retrieving webhook information...", nl=False)
    webhook_info = get_telegram_webhook_info(bot_token)

    if not webhook_info:
        click.secho(" ✗ Could not retrieve webhook info", fg="red")
        sys.exit(1)

    click.secho(" ✓ Retrieved", fg="green")
    click.echo()

    # Display webhook info
    click.echo("Webhook Configuration:")
    click.echo("─" * 50)

    url = webhook_info.get("url")
    if url:
        click.echo(f"URL:                 {url}")
    else:
        click.secho("URL:                 (not configured)", fg="yellow")

    has_secret = webhook_info.get("has_custom_certificate", False)
    click.echo(f"Has Secret Token:    {'Yes' if has_secret else 'No'}")

    pending = webhook_info.get("pending_update_count", 0)
    if pending > 0:
        click.secho(f"Pending Updates:     {pending}", fg="yellow")
    else:
        click.echo(f"Pending Updates:     {pending}")

    last_error_date = webhook_info.get("last_error_date")
    if last_error_date:
        click.secho(f"Last Error Date:     {last_error_date}", fg="yellow")
        click.secho(
            f"Last Error Message:  {webhook_info.get('last_error_message')}",
            fg="yellow",
        )
    else:
        click.secho("Last Error:          (none - webhook is healthy)", fg="green")

    click.echo("─" * 50)
    click.echo()


if __name__ == "__main__":
    cli()
