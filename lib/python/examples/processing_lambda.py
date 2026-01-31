"""
Example Lambda handler for async message processing.

This handler:
1. Receives message ID from SQS
2. Gets message from DynamoDB
3. Invokes Bedrock agent
4. Stores results (tasks, reminders) in DynamoDB
5. Queues response for delivery

Environment variables:
  - DYNAMODB_TABLE_NAME: Name of DynamoDB table
  - BEDROCK_AGENT_FUNCTION_NAME: Lambda function name of Bedrock agent
  - RESPONSE_QUEUE_URL: SQS queue for responses
  - AWS_REGION: AWS region
"""

import json
import os
import uuid
from datetime import datetime
import boto3

from second_brain_core import (
    Message,
    Task,
    Reminder,
    DynamoDBClient,
    MessageStatus,
    TaskStatus,
    ReminderRecurrence,
)


def invoke_bedrock_agent(user_id: str, message_content: str) -> dict:
    """
    Invoke Bedrock agent Lambda with message.

    Args:
        user_id: User ID
        message_content: Raw message text

    Returns:
        Agent response (should contain tasks, reminders, etc.)
    """
    lambda_client = boto3.client("lambda")
    agent_function = os.getenv("BEDROCK_AGENT_FUNCTION_NAME")

    if not agent_function:
        raise ValueError("BEDROCK_AGENT_FUNCTION_NAME environment variable not set")

    # Invoke agent synchronously
    response = lambda_client.invoke(
        FunctionName=agent_function,
        InvocationType="RequestResponse",
        Payload=json.dumps({
            "prompt": message_content,
            "user_id": user_id,
        }),
    )

    # Parse response
    response_payload = json.loads(response["Payload"].read())

    if response.get("FunctionError"):
        raise Exception(f"Agent error: {response_payload}")

    return response_payload


def queue_response_for_delivery(user_id: str, message_id: str, results: dict) -> None:
    """
    Queue response for delivery to user.

    Args:
        user_id: User ID
        message_id: Original message ID
        results: Processing results
    """
    sqs_client = boto3.client("sqs")
    queue_url = os.getenv("RESPONSE_QUEUE_URL")

    if not queue_url:
        raise ValueError("RESPONSE_QUEUE_URL environment variable not set")

    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({
            "user_id": user_id,
            "message_id": message_id,
            "results": results,
        }),
    )


def lambda_handler(event, context):
    """
    Process message with Bedrock agent and create tasks/reminders.

    Args:
        event: SQS Lambda event
        context: Lambda context

    Returns:
        Processing status
    """
    db_client = DynamoDBClient()

    # Process each SQS message
    for sqs_record in event.get("Records", []):
        try:
            # Parse SQS message body
            body = json.loads(sqs_record["body"])
            user_id = body["user_id"]
            message_id = body["message_id"]

            # 1. Get message from DynamoDB
            message = db_client.get_item(
                pk=f"user#{user_id}",
                sk=f"message#{message_id}",  # Note: This won't work without timestamp
                model_class=Message,
            )

            if not message:
                print(f"Message not found: {user_id}/{message_id}")
                continue

            # 2. Update message status
            db_client.update_item(
                pk=f"user#{user_id}",
                sk=f"message#{message.timestamp}#{message.message_id}",
                updates={"status": MessageStatus.PROCESSING.value},
            )

            # 3. Invoke Bedrock agent
            print(f"Invoking agent for {user_id}: {message.raw_content}")
            agent_response = invoke_bedrock_agent(user_id, message.raw_content)

            # 4. Process agent response and create items
            # Example: Agent returns {"tasks": [...], "reminders": [...]}
            created_items = []

            # Create tasks
            for task_data in agent_response.get("tasks", []):
                task = Task(
                    user_id=user_id,
                    task_id=str(uuid.uuid4()),
                    title=task_data.get("title"),
                    description=task_data.get("description"),
                    category=task_data.get("category", "general"),
                    priority=task_data.get("priority", "medium"),
                    due_date=task_data.get("due_date"),
                    source_message_id=message_id,
                )
                db_client.put_item(task)
                created_items.append({
                    "type": "task",
                    "id": task.task_id,
                    "title": task.title,
                })

            # Create reminders
            for reminder_data in agent_response.get("reminders", []):
                reminder = Reminder(
                    user_id=user_id,
                    reminder_id=str(uuid.uuid4()),
                    title=reminder_data.get("title"),
                    scheduled_for=reminder_data.get("scheduled_for"),
                    recurrence=reminder_data.get("recurrence", ReminderRecurrence.ONCE),
                    source_message_id=message_id,
                )
                db_client.put_item(reminder)
                created_items.append({
                    "type": "reminder",
                    "id": reminder.reminder_id,
                    "title": reminder.title,
                })

            # 5. Update message status to processed
            db_client.update_item(
                pk=f"user#{user_id}",
                sk=f"message#{message.timestamp}#{message.message_id}",
                updates={
                    "status": MessageStatus.PROCESSED.value,
                    "processed_at": datetime.utcnow().isoformat(),
                },
            )

            # 6. Queue response for delivery
            queue_response_for_delivery(
                user_id,
                message_id,
                {
                    "created_items": created_items,
                    "agent_response": agent_response.get("message"),
                },
            )

            print(f"✓ Processed message {message_id}: created {len(created_items)} items")

        except Exception as e:
            print(f"Error processing message: {e}")

            # Try to update message status to failed
            try:
                body = json.loads(sqs_record["body"])
                message_id = body["message_id"]
                db_client.update_item(
                    pk=f"user#{body['user_id']}",
                    sk=f"message#{message_id}",
                    updates={
                        "status": MessageStatus.FAILED.value,
                        "error_message": str(e),
                    },
                )
            except Exception:
                pass

            # Re-raise to trigger SQS retry
            raise

    return {"statusCode": 200, "body": "Processing complete"}


# Example for local testing
if __name__ == "__main__":
    example_sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "user_id": "user123",
                    "message_id": "msg_abc",
                })
            }
        ]
    }

    # Note: This won't work locally without DynamoDB and agent Lambda
    # but shows the structure
    print("See lambda_handler() for usage pattern")
