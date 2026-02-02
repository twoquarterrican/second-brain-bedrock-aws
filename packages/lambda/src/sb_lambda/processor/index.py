"""
Processing Lambda - Async Message Processor

Triggered by SQS messages, this Lambda:
1. Gets message from DynamoDB
2. Invokes Bedrock AgentCore runtime
3. Logs agent response
4. Queues response for delivery

The Bedrock agent handles all business logic including creating tasks,
reminders, todos, and other items via its tools.

Environment Variables:
  - DYNAMODB_TABLE_NAME
  - BEDROCK_AGENT_RUNTIME_ARN
  - AWS_REGION

TODO:
  - Update message status to PROCESSING and PROCESSED
  - Handle agent tool execution results
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


def invoke_bedrock_agent(user_id: str, message_content: str) -> None:
    """
    Invoke Bedrock AgentCore runtime.

    The agent processes the message and handles all business logic asynchronously:
    - Parses user intent
    - Creates tasks, reminders, todos via tools
    - Executes any other domain-specific operations
    - Logs its own activity

    The agent is responsible for logging and persisting all results via its tools.

    Args:
        user_id: User ID for session tracking
        message_content: Raw message text

    Note:
        Uses bedrock-agentcore InvokeAgentRuntime API with the runtime ARN.

    Raises:
        ValueError: If required environment variables are not set
        Exception: If agent invocation fails
    """
    agent_runtime_arn = os.getenv("BEDROCK_AGENT_RUNTIME_ARN")

    log_event(
        "agent_invocation_debug",
        {
            "agent_runtime_arn": agent_runtime_arn,
            "agent_runtime_arn_type": str(type(agent_runtime_arn)),
        },
    )

    if not agent_runtime_arn:
        raise ValueError("BEDROCK_AGENT_RUNTIME_ARN environment variable must be set")

    # Use bedrock-agentcore client (not bedrock-agent-runtime)
    client = boto3.client("bedrock-agentcore")

    # Prepare payload as JSON - must have "prompt" key for InvokeAgentRuntime API
    payload = json.dumps(
        {
            "prompt": message_content,
        }
    ).encode("utf-8")

    # Invoke agent runtime - it handles logging and tool execution internally
    client.invoke_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        contentType="application/json",
        payload=payload,
    )


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

                # Invoke Bedrock agent with structured instructions
                # Agent will use tools to process the message and respond to user
                prompt = f"""Process this message from the user:

Message ID: {message_id}
Message: {message.raw_content}

Please:
1. Use the classify_message tool to classify this message by topic/category
2. Use the find_similar_messages tool to search for related messages
3. Use the upsert_message tool to save or update this message in the knowledge base
4. Use the respond_to_user tool to summarize what you did and ask any follow-up questions

After processing:
- Classify the message
- Find similar messages to provide context
- Save/update the message
- Respond to the user with a brief summary of actions taken

Keep the user response concise and friendly. Ask follow-up questions only if needed.

Preserve the message ID: {message_id}
User ID: {user_id}"""

                invoke_bedrock_agent(user_id, prompt)

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
