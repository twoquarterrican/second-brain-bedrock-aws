# second-brain-core

Shared Python library for the Second Brain system.

Provides:
- **Models**: Pydantic data classes with DynamoDB serialization
- **Client**: DynamoDB operations wrapper
- **Constants**: Shared enums and patterns

## Installation

Install as editable dependency in projects that need it:

```bash
# From bedrock/
pip install -e ../../lib/python

# From root pyproject.toml
[dependencies]
second-brain-core = { path = "../lib/python", editable = true }
```

## Usage

```python
from second_brain_core import Task, DynamoDBClient

# Create a task
task = Task(
    user_id="user123",
    task_id="task_abc",
    title="Buy groceries",
    category="personal"
)

# Save to DynamoDB
client = DynamoDBClient()
client.put_item(task)

# Retrieve
retrieved = client.get_item("user123", "task#task_abc", Task)
```

## Models

- `Message` - Raw Telegram messages with processing status
- `Task` - Actionable items with priority and due dates
- `Todo` - Simple list items
- `Reminder` - Scheduled notifications

## Status Enums

- `MessageStatus` - received, processing, processed, failed, sent, archived
- `TaskStatus` - pending, completed, archived
- `ReminderStatus` - pending, sent, dismissed
