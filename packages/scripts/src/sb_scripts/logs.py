"""
CloudWatch Logs Navigation Script

Displays links to CloudWatch Logs for Second Brain components:
- Lambda function logs (message handler, processor)
- Bedrock Agent Core runtime logs

Run with: uv run logs
"""


import boto3
import click

from sb_scripts.utils import get_aws_region, load_env


def get_bedrock_agent_name() -> str:
    """Get Bedrock Agent runtime name from CloudFormation stack."""
    try:
        cfn = boto3.client("cloudformation")
        response = cfn.describe_stacks(StackName="SecondBrainStack")
        stacks = response.get("Stacks", [])

        if stacks:
            stack = stacks[0]
            for output in stack.get("Outputs", []):
                if output.get("ExportName") == "SecondBrainWebhookUrl":
                    # Agent name is typically in the runtime ARN
                    # For now, use a default pattern
                    return "second_brain_agent"

        return "second_brain_agent"
    except Exception:
        return "second_brain_agent"


@click.command()
def cli():
    """Display CloudWatch Logs links for Second Brain."""
    # Load environment variables
    load_env()

    region = get_aws_region()

    click.clear()
    click.secho("╔════════════════════════════════════════╗", fg="cyan")
    click.secho("║  Second Brain - CloudWatch Logs Links  ║", fg="cyan")
    click.secho("╚════════════════════════════════════════╝", fg="cyan")
    click.echo()

    # CloudWatch Logs console base URL
    base_url = f"https://console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups/log-group"

    logs = [
        {
            "name": "Message Handler (Telegram Webhook)",
            "log_group": "/aws/lambda/second-brain-message-handler",
            "description": "Webhook entry point - receives Telegram messages",
        },
        {
            "name": "Message Processor (SQS Worker)",
            "log_group": "/aws/lambda/second-brain-processor",
            "description": "Async processing - invokes Bedrock agent",
        },
        {
            "name": "Bedrock Agent Core Runtime",
            "log_group": "/aws/bedrock-agentcore/runtimes/second_brain_agent-*",
            "description": "Agent runtime execution logs",
        },
    ]

    click.echo("📋 CloudWatch Log Groups:")
    click.echo()

    for i, log in enumerate(logs, 1):
        click.secho(f"{i}. {log['name']}", fg="green", bold=True)
        click.echo(f"   {log['description']}")
        click.echo()

        # Generate direct CloudWatch Logs Insights link
        log_group_encoded = log["log_group"].replace("/", "%2F")
        direct_link = f"{base_url}%3A{log_group_encoded}:log-stream"
        click.echo(f"   🔗 {direct_link}")
        click.echo()

    click.echo("═" * 80)
    click.echo()

    click.echo("📊 Quick Commands:")
    click.echo()

    click.echo("View Message Handler logs:")
    click.secho(
        "  aws logs tail /aws/lambda/second-brain-message-handler --follow",
        fg="yellow",
    )
    click.echo()

    click.echo("View Message Processor logs:")
    click.secho(
        "  aws logs tail /aws/lambda/second-brain-processor --follow",
        fg="yellow",
    )
    click.echo()

    click.echo("View Agent Core runtime logs (last hour):")
    click.secho(
        "  aws logs tail /aws/bedrock-agentcore/runtimes/second_brain_agent-* --follow --since 1h",
        fg="yellow",
    )
    click.echo()

    click.echo("═" * 80)
    click.echo()

    click.echo("🔍 CloudWatch Logs Insights Queries:")
    click.echo()

    click.echo("Find all errors in Message Handler:")
    click.secho(
        "  fields @timestamp, @message | filter @message like /ERROR|error|Exception/ | stats count() by @message",
        fg="yellow",
    )
    click.echo()

    click.echo("Find processing latency:")
    click.secho(
        "  fields @duration | stats avg(@duration), max(@duration), pct(@duration, 95) by bin(5m)",
        fg="yellow",
    )
    click.echo()

    click.echo("Find all webhook calls with status:")
    click.secho(
        "  fields @timestamp, statusCode, @message | filter @message like /statusCode/",
        fg="yellow",
    )
    click.echo()

    click.echo("═" * 80)
    click.echo()

    click.echo("💡 Tips:")
    click.echo("  • Use --follow to stream logs in real-time")
    click.echo("  • Use --since 1h to view logs from the last hour")
    click.echo("  • Use --grep to filter by pattern: aws logs tail ... --grep ERROR")
    click.echo("  • CloudWatch Logs Insights allows complex queries and analysis")
    click.echo()


if __name__ == "__main__":
    cli()
