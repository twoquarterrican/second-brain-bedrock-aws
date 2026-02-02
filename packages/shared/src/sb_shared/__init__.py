"""Second Brain Core - Shared utilities and data models for Second Brain system.

This library provides:
- Pydantic models for all data types (Message, Task, Todo, Reminder)
- DynamoDB client for CRUD operations
- Constants and enums for consistent values
- Structured logging and observability utilities
"""

from .constants import (
    ItemType,
    MessageStatus,
    ReminderRecurrence,
    ReminderStatus,
    TaskPriority,
    TaskStatus,
)
from .dynamodb import DynamoDBClient
from .models import Message, Reminder, Task, Todo
from .observability import (
    ObservabilityContext,
    get_aws_request_id,
    lambda_handler,
    log_error,
    log_event,
    log_metrics,
    set_aws_request_id,
    setup_logging,
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
    # Observability
    "setup_logging",
    "log_event",
    "log_error",
    "log_metrics",
    "ObservabilityContext",
    "lambda_handler",
    "set_aws_request_id",
    "get_aws_request_id",
]
