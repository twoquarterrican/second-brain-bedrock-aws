"""
Example tests showing how to use second_brain_core models and client.

These examples show:
- Creating models
- Serializing to DynamoDB format
- Deserializing from DynamoDB format
- Using DynamoDB client (requires local DynamoDB)
"""

import json
from datetime import datetime
from second_brain_core import (
    Message,
    Task,
    Todo,
    Reminder,
    MessageStatus,
    TaskStatus,
    TaskPriority,
    ReminderRecurrence,
)


def example_message_model():
    """Create and serialize a Message model."""
    print("\n=== Message Model Example ===")

    # Create a message
    message = Message(
        user_id="user123",
        timestamp="2026-01-31T10:30:00Z",
        message_id="msg_abc123",
        telegram_message_id="12345",
        raw_content="Buy groceries and think about exercise",
        s3_key="raw-events/user123/2026/01/31/msg_abc123.json",
        status=MessageStatus.RECEIVED,
    )

    print(f"Created: {message}")

    # Convert to DynamoDB format
    dynamo_item = message.to_dynamo()
    print(f"\nAs DynamoDB item:\n{json.dumps(dynamo_item, indent=2)}")

    # Deserialize back from DynamoDB
    restored = Message.from_dynamo(dynamo_item)
    print(f"\nRestored: {restored}")
    assert restored.raw_content == message.raw_content


def example_task_model():
    """Create and serialize a Task model."""
    print("\n=== Task Model Example ===")

    # Create a task from agent decision
    task = Task(
        user_id="user123",
        task_id="task_xyz789",
        title="Buy groceries",
        description="milk, eggs, bread, vegetables",
        status=TaskStatus.PENDING,
        priority=TaskPriority.HIGH,
        category="personal",
        due_date="2026-02-05",
        source_message_id="msg_abc123",
    )

    print(f"Created: {task}")

    # Convert to DynamoDB format
    dynamo_item = task.to_dynamo()
    print(f"\nAs DynamoDB item:\n{json.dumps(dynamo_item, indent=2, default=str)}")

    # Deserialize back
    restored = Task.from_dynamo(dynamo_item)
    print(f"\nRestored: {restored}")
    assert restored.title == task.title
    assert restored.category == task.category


def example_reminder_model():
    """Create and serialize a Reminder model."""
    print("\n=== Reminder Model Example ===")

    # Create a reminder
    reminder = Reminder(
        user_id="user123",
        reminder_id="reminder_rem123",
        title="Morning exercise",
        scheduled_for="2026-02-01T06:00:00Z",
        recurrence=ReminderRecurrence.DAILY,
        source_message_id="msg_abc123",
    )

    print(f"Created: {reminder}")

    # Convert to DynamoDB format
    dynamo_item = reminder.to_dynamo()
    print(f"\nAs DynamoDB item:\n{json.dumps(dynamo_item, indent=2, default=str)}")

    # Deserialize back
    restored = Reminder.from_dynamo(dynamo_item)
    print(f"\nRestored: {restored}")
    assert restored.title == reminder.title
    assert restored.recurrence == reminder.recurrence


def example_todo_model():
    """Create and serialize a Todo model."""
    print("\n=== Todo Model Example ===")

    # Create todos
    todos = [
        Todo(
            user_id="user123",
            todo_id="todo_1",
            text="Call mom",
            completed=False,
            order=1,
        ),
        Todo(
            user_id="user123",
            todo_id="todo_2",
            text="Review project budget",
            completed=False,
            order=2,
        ),
    ]

    for todo in todos:
        print(f"\nCreated: {todo}")
        dynamo_item = todo.to_dynamo()
        print(f"As DynamoDB item:\n{json.dumps(dynamo_item, indent=2, default=str)}")

        # Deserialize back
        restored = Todo.from_dynamo(dynamo_item)
        assert restored.text == todo.text


def example_sort_key_generation():
    """Show how sort keys are generated from model data."""
    print("\n=== Sort Key Generation ===")

    # Message sort key
    message = Message(
        user_id="user123",
        timestamp="2026-01-31T10:30:00Z",
        message_id="msg_abc",
        telegram_message_id="12345",
        raw_content="test",
        s3_key="test",
    )
    print(f"Message SK: {message.sort_key}")
    # Output: message#2026-01-31T10:30:00Z#msg_abc

    # Task sort key
    task = Task(
        user_id="user123",
        task_id="task_xyz",
        title="Test",
        category="personal",
    )
    print(f"Task SK: {task.sort_key}")
    # Output: task#task_xyz

    # Todo sort key
    todo = Todo(
        user_id="user123",
        todo_id="todo_1",
        text="Test",
        order=1,
    )
    print(f"Todo SK: {todo.sort_key}")
    # Output: todo#todo_1

    # Reminder sort key
    reminder = Reminder(
        user_id="user123",
        reminder_id="rem_123",
        title="Test",
        scheduled_for="2026-02-01T06:00:00Z",
    )
    print(f"Reminder SK: {reminder.sort_key}")
    # Output: reminder#rem_123


def example_querying_pattern():
    """Show how to query items by sort key prefix."""
    print("\n=== Querying Pattern ===")

    user_id = "user123"

    # To query all tasks for a user:
    # client.query_by_pk_and_sk_prefix(
    #     pk=f"user#{user_id}",
    #     sk_prefix="task#",
    #     model_class=Task
    # )

    # To query all todos for a user:
    # client.query_by_pk_and_sk_prefix(
    #     pk=f"user#{user_id}",
    #     sk_prefix="todo#",
    #     model_class=Todo
    # )

    # To query all messages for a user:
    # client.query_by_pk_and_sk_prefix(
    #     pk=f"user#{user_id}",
    #     sk_prefix="message#",
    #     model_class=Message
    # )

    print("""
DynamoDB queries work by SK prefix:
- All tasks: sk_prefix="task#"
- All todos: sk_prefix="todo#"
- All messages: sk_prefix="message#"
- All reminders: sk_prefix="reminder#"

Messages also sort by timestamp (second # in SK):
message#2026-01-31T10:30:00Z#msg_abc
Queries naturally return in chronological order!
    """)


def example_updating_models():
    """Show how to update model values and save back."""
    print("\n=== Updating Models ===")

    # Create a task
    task = Task(
        user_id="user123",
        task_id="task_xyz",
        title="Buy groceries",
        status=TaskStatus.PENDING,
        category="personal",
    )

    print(f"Original: {task}")

    # To update in DynamoDB, use client.update_item()
    # which takes individual field updates:
    # client.update_item(
    #     pk="user#user123",
    #     sk="task#task_xyz",
    #     updates={
    #         "status": "completed",
    #         "completed_at": datetime.utcnow().isoformat()
    #     }
    # )

    print("""
To update a task, use DynamoDBClient.update_item():
client.update_item(
    pk="user#user123",
    sk="task#task_xyz",
    updates={
        "status": "completed",
        "completed_at": "2026-02-01T15:30:00Z"
    }
)
    """)


if __name__ == "__main__":
    print("Second Brain Core - Model Examples")
    print("=" * 50)

    example_message_model()
    example_task_model()
    example_reminder_model()
    example_todo_model()
    example_sort_key_generation()
    example_querying_pattern()
    example_updating_models()

    print("\n✓ All examples completed!")
