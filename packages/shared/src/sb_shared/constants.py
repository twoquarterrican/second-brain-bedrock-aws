"""Constants and enums for Second Brain."""

from enum import Enum
from typing import Dict


class MessageStatus(str, Enum):
    """Status of a message through processing pipeline."""

    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    SENT = "sent"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskPriority(str, Enum):
    """Priority level of a task."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReminderStatus(str, Enum):
    """Status of a reminder."""

    PENDING = "pending"
    SENT = "sent"
    DISMISSED = "dismissed"


class ReminderRecurrence(str, Enum):
    """Recurrence pattern for reminders."""

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ItemType(str, Enum):
    """Types of items stored in DynamoDB."""

    MESSAGE = "message"
    TASK = "task"
    TODO = "todo"
    REMINDER = "reminder"


# Sort Key Patterns
SK_PATTERNS: Dict[str, str] = {
    "message": "message#{timestamp}#{message_id}",
    "task": "task#{task_id}",
    "todo": "todo#{todo_id}",
    "reminder": "reminder#{reminder_id}",
}

# Default TTL (30 days in seconds)
DEFAULT_MESSAGE_TTL_SECONDS = 30 * 24 * 60 * 60

# DynamoDB table and S3 bucket names (read from environment)
# Note: These should be set at runtime via environment variables
DEFAULT_TABLE_NAME = "second-brain"
DEFAULT_BUCKET_NAME = "second-brain-data"

# S3 prefixes
S3_PREFIXES = {
    "raw_events": "raw-events",
    "vector_embeddings": "vector-embeddings",
    "backups": "backups",
}
