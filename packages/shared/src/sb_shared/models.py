"""Pydantic models for Second Brain with DynamoDB serialization."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .constants import (
    DEFAULT_MESSAGE_TTL_SECONDS,
    ItemType,
    MessageStatus,
    ReminderRecurrence,
    ReminderStatus,
    TaskPriority,
    TaskStatus,
)


class Message(BaseModel):
    """Raw message from Telegram, immutable metadata."""

    # Primary keys
    user_id: str = Field(description="User ID (maps to DynamoDB PK)")
    timestamp: str = Field(description="ISO timestamp for ordering (part of SK)")
    message_id: str = Field(description="Unique message ID (part of SK)")

    # Message content
    telegram_message_id: str = Field(description="Telegram message ID for reply")
    raw_content: str = Field(description="The actual message text")

    # Storage
    s3_key: str = Field(description="Path to immutable raw event in S3")

    # Processing status
    status: MessageStatus = Field(
        default=MessageStatus.RECEIVED,
        description="Stage in processing pipeline",
    )

    # Metadata
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When message was received",
    )
    processed_at: Optional[str] = Field(default=None, description="When message was processed")
    error_message: Optional[str] = Field(
        default=None, description="Error details if processing failed"
    )

    # DynamoDB TTL (30 days)
    ttl: int = Field(
        default_factory=lambda: int((datetime.utcnow().timestamp() + DEFAULT_MESSAGE_TTL_SECONDS)),
        description="Unix timestamp for auto-delete",
    )

    # GSI support - models decide their own GSI1PK/GSI1SK or leave unset
    gsi1_pk: Optional[str] = Field(
        default=None, description="GSI1 partition key (defined by model)"
    )
    gsi1_sk: Optional[str] = Field(default=None, description="GSI1 sort key (defined by model)")

    # Internal
    type: str = Field(default=ItemType.MESSAGE.value, description="Item type for filtering")

    class Config:
        """Pydantic config."""

        use_enum_values = True

    @property
    def sort_key(self) -> str:
        """Generate DynamoDB sort key."""
        return f"message#{self.timestamp}#{self.message_id}"

    def to_dynamo(self) -> dict:
        """Convert to DynamoDB item format."""
        data = self.model_dump(exclude={"user_id"}, exclude_none=False)
        item = {
            "PK": self.user_id,
            "SK": self.sort_key,
            **data,
        }
        # Only include GSI keys if set
        if self.gsi1_pk is not None:
            item["GSI1PK"] = self.gsi1_pk
        if self.gsi1_sk is not None:
            item["GSI1SK"] = self.gsi1_sk
        return item

    @classmethod
    def from_dynamo(cls, item: dict) -> "Message":
        """Create model from DynamoDB item."""
        # Extract keys
        user_id = item.pop("PK")
        sk = item.pop("SK")

        # Parse SK to extract timestamp and message_id
        # Format: message#{timestamp}#{message_id}
        parts = sk.split("#")
        if len(parts) != 3:
            raise ValueError(f"Invalid SK format: {sk}")

        timestamp = parts[1]
        message_id = parts[2]

        return cls(user_id=user_id, timestamp=timestamp, message_id=message_id, **item)


class Task(BaseModel):
    """Actionable task extracted from messages."""

    # Primary keys
    user_id: str = Field(description="User ID (maps to DynamoDB PK)")
    task_id: str = Field(description="Unique task ID (part of SK)")

    # Task content
    title: str = Field(description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")

    # Task properties
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    due_date: Optional[str] = Field(default=None, description="Due date in ISO format")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Priority level")
    category: str = Field(description="Category (work, personal, health, etc) - evolves over time")

    # Traceability
    source_message_id: Optional[str] = Field(
        default=None, description="Original message this was extracted from"
    )

    # Metadata
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When task was created",
    )
    updated_at: Optional[str] = Field(default=None, description="Last update timestamp")
    completed_at: Optional[str] = Field(default=None, description="When task was completed")

    # GSI support - models decide their own GSI1PK/GSI1SK or leave unset
    gsi1_pk: Optional[str] = Field(
        default=None, description="GSI1 partition key (defined by model)"
    )
    gsi1_sk: Optional[str] = Field(default=None, description="GSI1 sort key (defined by model)")

    # Internal
    type: str = Field(default=ItemType.TASK.value, description="Item type for filtering")

    class Config:
        """Pydantic config."""

        use_enum_values = True

    @property
    def sort_key(self) -> str:
        """Generate DynamoDB sort key."""
        return f"task#{self.task_id}"

    def to_dynamo(self) -> dict:
        """Convert to DynamoDB item format."""
        data = self.model_dump(exclude={"user_id"}, exclude_none=False)
        item = {
            "PK": self.user_id,
            "SK": self.sort_key,
            **data,
        }
        # Only include GSI keys if set
        if self.gsi1_pk is not None:
            item["GSI1PK"] = self.gsi1_pk
        if self.gsi1_sk is not None:
            item["GSI1SK"] = self.gsi1_sk
        return item

    @classmethod
    def from_dynamo(cls, item: dict) -> "Task":
        """Create model from DynamoDB item."""
        user_id = item.pop("PK")
        sk = item.pop("SK")

        # Parse SK to extract task_id
        # Format: task#{task_id}
        parts = sk.split("#")
        if len(parts) != 2:
            raise ValueError(f"Invalid SK format: {sk}")

        task_id = parts[1]

        return cls(user_id=user_id, task_id=task_id, **item)


class Todo(BaseModel):
    """Simple todo item without deadline structure."""

    # Primary keys
    user_id: str = Field(description="User ID (maps to DynamoDB PK)")
    todo_id: str = Field(description="Unique todo ID (part of SK)")

    # Content
    text: str = Field(description="Todo text")

    # State
    completed: bool = Field(default=False, description="Whether todo is done")
    order: int = Field(description="Position in list for ordering")

    # Metadata
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When todo was created",
    )

    # GSI support - models decide their own GSI1PK/GSI1SK or leave unset
    gsi1_pk: Optional[str] = Field(
        default=None, description="GSI1 partition key (defined by model)"
    )
    gsi1_sk: Optional[str] = Field(default=None, description="GSI1 sort key (defined by model)")

    # Internal
    type: str = Field(default=ItemType.TODO.value, description="Item type for filtering")

    class Config:
        """Pydantic config."""

        use_enum_values = True

    @property
    def sort_key(self) -> str:
        """Generate DynamoDB sort key."""
        return f"todo#{self.todo_id}"

    def to_dynamo(self) -> dict:
        """Convert to DynamoDB item format."""
        data = self.model_dump(exclude={"user_id"}, exclude_none=False)
        item = {
            "PK": self.user_id,
            "SK": self.sort_key,
            **data,
        }
        # Only include GSI keys if set
        if self.gsi1_pk is not None:
            item["GSI1PK"] = self.gsi1_pk
        if self.gsi1_sk is not None:
            item["GSI1SK"] = self.gsi1_sk
        return item

    @classmethod
    def from_dynamo(cls, item: dict) -> "Todo":
        """Create model from DynamoDB item."""
        user_id = item.pop("PK")
        sk = item.pop("SK")

        # Parse SK to extract todo_id
        # Format: todo#{todo_id}
        parts = sk.split("#")
        if len(parts) != 2:
            raise ValueError(f"Invalid SK format: {sk}")

        todo_id = parts[1]

        return cls(user_id=user_id, todo_id=todo_id, **item)


class Reminder(BaseModel):
    """Scheduled notification with optional recurrence."""

    # Primary keys
    user_id: str = Field(description="User ID (maps to DynamoDB PK)")
    reminder_id: str = Field(description="Unique reminder ID (part of SK)")

    # Content
    title: str = Field(description="Reminder title")

    # Scheduling
    scheduled_for: str = Field(description="When to send reminder (ISO timestamp)")
    recurrence: ReminderRecurrence = Field(
        default=ReminderRecurrence.ONCE, description="Recurrence pattern"
    )

    # Status
    status: ReminderStatus = Field(
        default=ReminderStatus.PENDING, description="Current reminder status"
    )

    # Traceability
    source_message_id: Optional[str] = Field(
        default=None, description="Original message this was extracted from"
    )

    # Metadata
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When reminder was created",
    )
    sent_at: Optional[str] = Field(default=None, description="When reminder was sent")

    # GSI support - models decide their own GSI1PK/GSI1SK or leave unset
    gsi1_pk: Optional[str] = Field(
        default=None, description="GSI1 partition key (defined by model)"
    )
    gsi1_sk: Optional[str] = Field(default=None, description="GSI1 sort key (defined by model)")

    # Internal
    type: str = Field(default=ItemType.REMINDER.value, description="Item type for filtering")

    class Config:
        """Pydantic config."""

        use_enum_values = True

    @property
    def sort_key(self) -> str:
        """Generate DynamoDB sort key."""
        return f"reminder#{self.reminder_id}"

    def to_dynamo(self) -> dict:
        """Convert to DynamoDB item format."""
        data = self.model_dump(exclude={"user_id"}, exclude_none=False)
        item = {
            "PK": self.user_id,
            "SK": self.sort_key,
            **data,
        }
        # Only include GSI keys if set
        if self.gsi1_pk is not None:
            item["GSI1PK"] = self.gsi1_pk
        if self.gsi1_sk is not None:
            item["GSI1SK"] = self.gsi1_sk
        return item

    @classmethod
    def from_dynamo(cls, item: dict) -> "Reminder":
        """Create model from DynamoDB item."""
        user_id = item.pop("PK")
        sk = item.pop("SK")

        # Parse SK to extract reminder_id
        # Format: reminder#{reminder_id}
        parts = sk.split("#")
        if len(parts) != 2:
            raise ValueError(f"Invalid SK format: {sk}")

        reminder_id = parts[1]

        return cls(user_id=user_id, reminder_id=reminder_id, **item)
