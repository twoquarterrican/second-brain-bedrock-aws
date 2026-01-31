"""
Processing Lambda - Async Message Processor

Triggered by SQS messages, this Lambda:
1. Gets message from DynamoDB
2. Invokes Bedrock agent
3. Creates tasks/reminders from results
4. Updates message status
5. Queues response for delivery

Environment Variables:
  - DYNAMODB_TABLE_NAME
  - S3_BUCKET_NAME
  - BEDROCK_AGENT_FUNCTION_NAME
  - AWS_REGION

TODO:
  - Create response queue and wire it
  - Implement retry logic for agent invocation
  - Handle agent errors gracefully
  - Create response Lambda to send back to Telegram
  - Add metrics for processing latency
  - Add support for streaming agent responses
"""

import json
import os
import uuid
from datetime import datetime
import boto3
import sys

# Add shared library to path
sys.path.insert(0, '/opt/python')

from second_brain_core import (
    Message,
    Task,
    Reminder,
    Todo,
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

    TODO:
      - Handle streaming responses
      - Add timeout handling
      - Implement circuit breaker
    """
    lambda_client = boto3.client('lambda')
    agent_function = os.getenv('BEDROCK_AGENT_FUNCTION_NAME')

    if not agent_function:
        raise ValueError('BEDROCK_AGENT_FUNCTION_NAME environment variable not set')

    # Invoke agent synchronously
    response = lambda_client.invoke(
        FunctionName=agent_function,
        InvocationType='RequestResponse',
        Payload=json.dumps({
            'prompt': message_content,
            'user_id': user_id,
        }),
    )

    # Parse response
    response_payload = json.loads(response['Payload'].read())

    if response.get('FunctionError'):
        raise Exception(f"Agent error: {response_payload}")

    return response_payload


def create_tasks_from_agent_response(
    user_id: str,
    message_id: str,
    agent_response: dict,
    db_client: DynamoDBClient,
) -> list:
    """
    Create Task items from agent response.

    Args:
        user_id: User ID
        message_id: Original message ID
        agent_response: Response from Bedrock agent
        db_client: DynamoDB client

    Returns:
        List of created task IDs

    TODO:
      - Validate task data
      - Handle duplicate detection
      - Support task dependencies
      - Add priority calculation
    """
    created_tasks = []

    for task_data in agent_response.get('tasks', []):
        try:
            task = Task(
                user_id=user_id,
                task_id=str(uuid.uuid4()),
                title=task_data.get('title'),
                description=task_data.get('description'),
                category=task_data.get('category', 'general'),
                priority=task_data.get('priority', TaskStatus.PENDING),
                due_date=task_data.get('due_date'),
                source_message_id=message_id,
            )
            db_client.put_item(task)
            created_tasks.append(task.task_id)

            print(json.dumps({
                'observability': 'task_created',
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'task_id': task.task_id,
                'category': task.category,
            }), file=sys.stderr)

        except Exception as e:
            print(f'Error creating task: {e}', file=sys.stderr)

    return created_tasks


def create_reminders_from_agent_response(
    user_id: str,
    message_id: str,
    agent_response: dict,
    db_client: DynamoDBClient,
) -> list:
    """
    Create Reminder items from agent response.

    Args:
        user_id: User ID
        message_id: Original message ID
        agent_response: Response from Bedrock agent
        db_client: DynamoDB client

    Returns:
        List of created reminder IDs

    TODO:
      - Validate scheduled times
      - Handle invalid recurrence patterns
      - Create EventBridge rules for actual reminders
    """
    created_reminders = []

    for reminder_data in agent_response.get('reminders', []):
        try:
            reminder = Reminder(
                user_id=user_id,
                reminder_id=str(uuid.uuid4()),
                title=reminder_data.get('title'),
                scheduled_for=reminder_data.get('scheduled_for'),
                recurrence=reminder_data.get('recurrence', ReminderRecurrence.ONCE),
                source_message_id=message_id,
            )
            db_client.put_item(reminder)
            created_reminders.append(reminder.reminder_id)

            print(json.dumps({
                'observability': 'reminder_created',
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'reminder_id': reminder.reminder_id,
                'scheduled_for': reminder.scheduled_for,
            }), file=sys.stderr)

        except Exception as e:
            print(f'Error creating reminder: {e}', file=sys.stderr)

    return created_reminders


def create_todos_from_agent_response(
    user_id: str,
    message_id: str,
    agent_response: dict,
    db_client: DynamoDBClient,
) -> list:
    """
    Create Todo items from agent response.

    Args:
        user_id: User ID
        message_id: Original message ID
        agent_response: Response from Bedrock agent
        db_client: DynamoDB client

    Returns:
        List of created todo IDs

    TODO:
      - Support bulk todo creation
      - Auto-order todos
    """
    created_todos = []

    for idx, todo_data in enumerate(agent_response.get('todos', [])):
        try:
            todo = Todo(
                user_id=user_id,
                todo_id=str(uuid.uuid4()),
                text=todo_data.get('text'),
                completed=False,
                order=idx,
            )
            db_client.put_item(todo)
            created_todos.append(todo.todo_id)

        except Exception as e:
            print(f'Error creating todo: {e}', file=sys.stderr)

    return created_todos


def queue_response_for_delivery(user_id: str, message_id: str, results: dict) -> None:
    """
    Queue response for delivery to user.

    Args:
        user_id: User ID
        message_id: Original message ID
        results: Processing results

    TODO:
      - Create response queue
      - Add retry queue
    """
    # TODO: Implement response queue
    print(json.dumps({
        'observability': 'response_queued',
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'message_id': message_id,
        'num_items': len(results.get('created_items', [])),
    }), file=sys.stderr)


def lambda_handler(event, context):
    """
    Process SQS messages with Bedrock agent and create tasks/reminders.

    Args:
        event: SQS Lambda event
        context: Lambda context

    Returns:
        Processing status
    """
    db_client = DynamoDBClient()
    table_name = os.getenv('DYNAMODB_TABLE_NAME')

    # Process each SQS message
    for sqs_record in event.get('Records', []):
        message_id = None
        user_id = None
        message = None

        try:
            # Parse SQS message body
            body = json.loads(sqs_record['body'])
            user_id = body['user_id']
            message_id = body['message_id']

            print(json.dumps({
                'observability': 'processing_started',
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'message_id': message_id,
            }), file=sys.stderr)

            # TODO: Get message from DynamoDB
            # Need to query by timestamp since it's part of SK
            # For now, stub out the retrieval
            # message = db_client.get_item(
            #     pk=f"user#{user_id}",
            #     sk=f"message#{message_id}",
            #     model_class=Message,
            # )

            # if not message:
            #     print(f"Message not found: {user_id}/{message_id}")
            #     continue

            # 2. Update message status
            # TODO: Need timestamp from SK to update properly
            # db_client.update_item(
            #     pk=f"user#{user_id}",
            #     sk=f"message#{message.timestamp}#{message.message_id}",
            #     updates={'status': MessageStatus.PROCESSING.value},
            # )

            # 3. Invoke Bedrock agent
            print(f"Invoking agent for {user_id}: message_id={message_id}")

            # TODO: Get actual message content
            # For now, stub response
            # agent_response = invoke_bedrock_agent(user_id, message.raw_content)

            agent_response = {
                'tasks': [
                    {
                        'title': 'TODO: Implement agent response parsing',
                        'category': 'general',
                        'priority': 'medium',
                    }
                ],
                'reminders': [],
                'todos': [],
                'message': 'Agent response parsing not yet implemented',
            }

            # 4. Process agent response and create items
            created_items = []

            # Create tasks
            created_task_ids = create_tasks_from_agent_response(
                user_id, message_id, agent_response, db_client
            )
            created_items.extend([
                {'type': 'task', 'id': tid}
                for tid in created_task_ids
            ])

            # Create reminders
            created_reminder_ids = create_reminders_from_agent_response(
                user_id, message_id, agent_response, db_client
            )
            created_items.extend([
                {'type': 'reminder', 'id': rid}
                for rid in created_reminder_ids
            ])

            # Create todos
            created_todo_ids = create_todos_from_agent_response(
                user_id, message_id, agent_response, db_client
            )
            created_items.extend([
                {'type': 'todo', 'id': tid}
                for tid in created_todo_ids
            ])

            # 5. Update message status to processed
            # TODO: Fix update with proper SK
            # db_client.update_item(
            #     pk=f"user#{user_id}",
            #     sk=f"message#{message.timestamp}#{message.message_id}",
            #     updates={
            #         'status': MessageStatus.PROCESSED.value,
            #         'processed_at': datetime.utcnow().isoformat(),
            #     },
            # )

            # 6. Queue response for delivery
            queue_response_for_delivery(
                user_id,
                message_id,
                {
                    'created_items': created_items,
                    'agent_response': agent_response.get('message'),
                },
            )

            print(json.dumps({
                'observability': 'message_processed',
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'message_id': message_id,
                'num_items_created': len(created_items),
            }), file=sys.stderr)

        except Exception as e:
            print(f'Error processing message: {e}', file=sys.stderr)

            # Log error event
            print(json.dumps({
                'observability': 'processing_error',
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'message_id': message_id,
                'error': str(e),
            }), file=sys.stderr)

            # TODO: Update message status to failed
            # Re-raise to trigger SQS retry
            raise

    return {'statusCode': 200, 'body': 'Processing complete'}
