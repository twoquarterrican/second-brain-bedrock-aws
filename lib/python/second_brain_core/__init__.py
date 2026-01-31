"""Second Brain Core - Shared utilities and data models for Second Brain system.

This library provides:
- Pydantic models for all data types (Message, Task, Todo, Reminder)
- DynamoDB client for CRUD operations
- Constants and enums for consistent values
"""

from .models import Message, Task, Todo, Reminder
from .dynamodb import DynamoDBClient
from .constants import (
    MessageStatus,
    TaskStatus,
    TaskPriority,
    ReminderStatus,
    ReminderRecurrence,
    ItemType,
)

__version__ = "0.1.0"

__all__ = [
    # Models
    "Message",
    "Task",
    "Todo",
    "Reminder",
    # Client
    "DynamoDBClient",
    # Constants
    "MessageStatus",
    "TaskStatus",
    "TaskPriority",
    "ReminderStatus",
    "ReminderRecurrence",
    "ItemType",
]
