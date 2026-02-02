"""
Processing Lambda - Async Message Processor

Triggered by SQS messages, this Lambda:
1. Gets message from DynamoDB
2. Invokes Bedrock agent via Agents Runtime API
3. Logs agent response
4. Queues response for delivery

The Bedrock agent handles all business logic including creating tasks,
reminders, todos, and other items via its tools.

Environment Variables:
  - DYNAMODB_TABLE_NAME
  - BEDROCK_AGENT_ID
  - BEDROCK_AGENT_ALIAS_ID
  - AWS_REGION

TODO:
  - Handle streaming agent responses
  - Implement retry logic for agent invocation
  - Update message status to PROCESSING and PROCESSED
"""

import json
import os

import boto3
from sb_shared import (
    DynamoDBClient,
    Message,
    ObservabilityContext,
    lambda_handler,
    log_error,
    log_event,
)


def invoke_bedrock_agent(user_id: str, message_content: str) -> dict:
    """
    Invoke Bedrock agent via Agents Runtime API.

    The agent processes the message and handles all business logic
    including creating tasks, reminders, and other items via tools.

    Args:
        user_id: User ID for session tracking
        message_content: Raw message text

    Returns:
        Agent response from invoke_agent API

    Raises:
        ValueError: If required environment variables are not set
        Exception: If agent invocation fails

    Agent Alias (ASIS):
        ASIS (As-Is) is the standard Bedrock Agents alias that automatically
        routes to the latest unpromoted agent version. This allows the agent
        to be updated without requiring code changes to update alias references.
    """
    agent_id = os.getenv("BEDROCK_AGENT_ID")
    agent_alias_id = os.getenv("BEDROCK_AGENT_ALIAS_ID")

    if not agent_id or not agent_alias_id:
        raise ValueError(
            "BEDROCK_AGENT_ID and BEDROCK_AGENT_ALIAS_ID environment variables must be set"
        )

    client = boto3.client("bedrock-agent-runtime")

    # Use user_id as session ID for consistent conversation context
    session_id = user_id

    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        inputText=message_content,
    )

    return response


@lambda_handler(kind="sqs")
def lambda_handler(event, _context):
    """
    Process SQS messages by invoking Bedrock agent.

    For each message:
    1. Parse SQS record
    2. Get message from DynamoDB
    3. Invoke Bedrock agent (handles all business logic via tools)
    4. Log response

    Args:
        event: SQS Lambda event
        _context: Lambda context

    Returns:
        Processing status
    """
    # Process each SQS message
    for sqs_record in event.get("Records", []):
        message_id = None
        user_id = None

        try:
            # Parse SQS message body
            body = json.loads(sqs_record["body"])
            user_id = body["user_id"]
            message_id = body["message_id"]
            timestamp = body["timestamp"]

            # Log operation with timing
            with ObservabilityContext(
                "process_message",
                {
                    "user_id": user_id,
                    "message_id": message_id,
                },
            ):
                # Get message from DynamoDB to retrieve raw_content
                db_client = DynamoDBClient()
                message = db_client.get_item(
                    pk=Message.pk_for(user_id=user_id),
                    sk=Message.sk_for(timestamp=timestamp, message_id=message_id),
                    model_class=Message,
                )

                if not message:
                    raise ValueError(
                        f"Message not found: user_id={user_id}, message_id={message_id}"
                    )

                # Invoke Bedrock agent
                # Agent handles all business logic including:
                # - Parsing user intent
                # - Creating tasks, reminders, todos via tools
                # - Any other domain-specific operations
                invoke_bedrock_agent(user_id, message.raw_content)

                # Log agent invocation
                log_event(
                    "agent_invoked",
                    {
                        "user_id": user_id,
                        "message_id": message_id,
                    },
                )

        except Exception as e:
            # Log error event
            log_error(
                "processing_error",
                e,
                {
                    "user_id": user_id,
                    "message_id": message_id,
                },
            )

            # Re-raise to trigger SQS retry
            raise

    return {"statusCode": 200, "body": "Processing complete"}
