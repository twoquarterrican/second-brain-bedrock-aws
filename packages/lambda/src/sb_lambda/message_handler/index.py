"""
Message Handler Lambda - Telegram Webhook Entry Point

Receives Telegram messages and:
1. Validates Telegram webhook signature (X-Telegram-Bot-Api-Secret-Token)
2. Saves raw message to S3 (immutable)
3. Saves metadata to DynamoDB
4. Queues for async processing
5. Returns 200 OK immediately

Environment Variables:
  - DYNAMODB_TABLE_NAME
  - S3_BUCKET_NAME
  - MESSAGE_QUEUE_URL
  - TELEGRAM_SECRET_TOKEN (required for webhook security)
  - AWS_REGION

TODO:
  - Handle message edits and deletions
  - Support message attachments (photos, files)
  - Rate limiting per user
"""

import hmac
import json
import os
import uuid
from datetime import datetime

import boto3
from sb_shared import DynamoDBClient, Message, MessageStatus, log_error, log_event, setup_logging


def verify_telegram_secret_token(headers: dict) -> bool:
    """
    Verify the X-Telegram-Bot-Api-Secret-Token header.

    Telegram includes this header in every webhook request. Must match the
    secret token configured when setting the webhook.

    Args:
        headers: Request headers dict (case-insensitive keys)

    Returns:
        True if token is valid, False otherwise
    """
    secret_token = os.getenv("TELEGRAM_SECRET_TOKEN")
    if not secret_token:
        # If no secret token is configured, reject all requests (fail secure)
        return False

    # Get token from header (case-insensitive lookup)
    token_from_header = None
    for key, value in headers.items():
        if key.lower() == "x-telegram-bot-api-secret-token":
            token_from_header = value
            break

    if not token_from_header:
        return False

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(token_from_header, secret_token)


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
    bucket_name = os.getenv("S3_BUCKET_NAME")

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

    Args:
        event: API Gateway Lambda proxy integration event
        context: Lambda context

    Returns:
        API Gateway Lambda proxy integration response
    """
    # Setup structured logging
    setup_logging()

    try:
        # Verify Telegram webhook signature (security: must match before processing)
        headers = event.get("headers", {})
        if not verify_telegram_secret_token(headers):
            log_event("webhook_unauthorized", {"reason": "invalid_or_missing_token"})
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Unauthorized"}),
            }

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
        # TODO: Extract actual user_id from auth token
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

        # 5. Log observability event
        log_event(
            "message_received",
            {
                "user_id": user_id,
                "message_id": message_id,
                "s3_key": s3_key,
                "raw_length": len(raw_text),
            },
        )

        # 6. Return success immediately
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "received",
                    "message_id": message_id,
                    "user_id": user_id,
                }
            ),
        }

    except Exception as e:
        # Log error event
        log_error("message_handler_error", e)

        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
