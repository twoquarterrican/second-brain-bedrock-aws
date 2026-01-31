"""
Example Lambda handler for Telegram webhook.

This shows how to use second_brain_core models and client.

Environment variables:
  - DYNAMODB_TABLE_NAME: Name of DynamoDB table
  - S3_BUCKET_NAME: Name of S3 bucket
  - AWS_REGION: AWS region
"""

import json
import os
import uuid
from datetime import datetime
import boto3

from second_brain_core import Message, DynamoDBClient, MessageStatus


def save_raw_event_to_s3(user_id: str, message_id: str, raw_message: dict) -> str:
    """
    Save raw Telegram message to S3 immutable log.

    Args:
        user_id: User identifier
        message_id: Message identifier
        raw_message: Raw message dict from Telegram

    Returns:
        S3 key for the saved message
    """
    s3_client = boto3.client("s3")
    bucket_name = os.getenv("S3_BUCKET_NAME", "second-brain-data")

    # Create S3 key: raw-events/user_id/YYYY/MM/DD/message_id.json
    now = datetime.utcnow()
    s3_key = (
        f"raw-events/{user_id}/"
        f"{now.year:04d}/{now.month:02d}/{now.day:02d}/"
        f"{message_id}.json"
    )

    # Save with immutable storage
    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=json.dumps(raw_message),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )

    return s3_key


def queue_message_for_processing(message_id: str, user_id: str) -> None:
    """
    Queue message for async processing via SQS.

    Args:
        message_id: Message to process
        user_id: User who sent message
    """
    sqs_client = boto3.client("sqs")
    queue_url = os.getenv("MESSAGE_QUEUE_URL")

    if not queue_url:
        raise ValueError("MESSAGE_QUEUE_URL environment variable not set")

    sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({"user_id": user_id, "message_id": message_id}),
    )


def lambda_handler(event, context):
    """
    Handle Telegram webhook POST request.

    Telegram sends a JSON body with message data. This handler:
    1. Parses the Telegram message
    2. Saves raw message to S3 (immutable)
    3. Saves metadata to DynamoDB
    4. Queues for async processing
    5. Returns 200 OK immediately

    Args:
        event: API Gateway Lambda proxy integration event
        context: Lambda context

    Returns:
        API Gateway Lambda proxy integration response
    """
    try:
        # Parse webhook payload
        body = json.loads(event.get("body", "{}"))
        telegram_message = body.get("message", {})

        if not telegram_message:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No message in payload"}),
            }

        # Extract message details
        telegram_message_id = telegram_message.get("message_id")
        chat_id = telegram_message.get("chat", {}).get("id")
        raw_text = telegram_message.get("text", "")

        if not raw_text:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No text in message"}),
            }

        # Use chat_id as user_id for single-user setup
        # Later: extract actual user_id from auth token
        user_id = str(chat_id)

        # Generate message ID
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # 1. Save raw event to S3 (immutable)
        s3_key = save_raw_event_to_s3(user_id, message_id, telegram_message)

        # 2. Create Message model
        message = Message(
            user_id=user_id,
            timestamp=timestamp,
            message_id=message_id,
            telegram_message_id=str(telegram_message_id),
            raw_content=raw_text,
            s3_key=s3_key,
            status=MessageStatus.RECEIVED,
        )

        # 3. Save to DynamoDB
        db_client = DynamoDBClient()
        db_client.put_item(message)

        # 4. Queue for processing
        queue_message_for_processing(message_id, user_id)

        # 5. Return success immediately
        return {
            "statusCode": 200,
            "body": json.dumps({
                "status": "received",
                "message_id": message_id,
                "user_id": user_id,
            }),
        }

    except Exception as e:
        print(f"Error in message handler: {e}", flush=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


# Example event for local testing
if __name__ == "__main__":
    example_event = {
        "body": json.dumps({
            "message": {
                "message_id": 12345,
                "chat": {"id": 67890},
                "text": "Buy groceries and think about exercise",
            }
        })
    }

    result = lambda_handler(example_event, None)
    print(json.dumps(result, indent=2))
