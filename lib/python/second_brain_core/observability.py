"""Observability utilities for structured logging in CloudWatch.

Provides helpers for emitting structured logs that are easy to query
in CloudWatch Logs Insights.

Example:
    ```python
    from second_brain_core import log_event

    log_event('message_received', {
        'user_id': 'user123',
        'message_id': 'msg_abc',
        'source': 'telegram'
    })
    ```

CloudWatch Logs Insights Query:
    ```
    fields @timestamp, eventType, user_id, message_id
    | stats count() by eventType
    | sort count() desc
    ```
"""

import json
import logging
from typing import Any, Dict, Optional

# Initialize AWS Lambda logging
try:
    import aws_lambda_logging

    HAS_LAMBDA_LOGGING = True
except ImportError:
    HAS_LAMBDA_LOGGING = False


def setup_logging() -> None:
    """
    Set up AWS Lambda structured logging.

    Call this at the start of your Lambda handler.
    """
    if HAS_LAMBDA_LOGGING:
        aws_lambda_logging.setup(
            level="INFO",
            boto_request_log_level="INFO",
        )


def log_event(
    event_type: str,
    details: Optional[Dict[str, Any]] = None,
    level: str = "INFO",
) -> None:
    """
    Log a structured observability event.

    Args:
        event_type: Type of event (e.g., 'message_received', 'task_created')
        details: Additional context (user_id, message_id, etc.)
        level: Log level ('INFO', 'WARNING', 'ERROR')

    Example:
        ```python
        log_event('task_created', {
            'user_id': 'user123',
            'task_id': 'task_abc',
            'category': 'personal'
        })
        ```

    CloudWatch Logs Insights Query:
        ```
        fields @timestamp, eventType, user_id, task_id, category
        | filter eventType = "task_created"
        | stats count() by category
        ```
    """
    if details is None:
        details = {}

    # Create structured log entry
    log_entry = {
        "eventType": event_type,
        **details,
    }

    # Get logger and log with appropriate level
    logger = logging.getLogger()

    if level == "WARNING":
        logger.warning(json.dumps(log_entry))
    elif level == "ERROR":
        logger.error(json.dumps(log_entry))
    else:
        logger.info(json.dumps(log_entry))


def log_error(
    event_type: str,
    error: Exception,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log an error event with exception details.

    Args:
        event_type: Type of error event (e.g., 'message_handler_error')
        error: The exception that occurred
        details: Additional context

    Example:
        ```python
        try:
            do_something()
        except Exception as e:
            log_error('task_creation_failed', e, {
                'user_id': 'user123',
                'reason': 'invalid_category'
            })
        ```

    CloudWatch Logs Insights Query:
        ```
        fields @timestamp, eventType, user_id, error
        | filter eventType like /error/
        | stats count() by eventType
        ```
    """
    if details is None:
        details = {}

    log_entry = {
        "eventType": event_type,
        "error": str(error),
        "errorType": type(error).__name__,
        **details,
    }

    logger = logging.getLogger()
    logger.error(json.dumps(log_entry))


def log_metrics(
    event_type: str,
    metrics: Dict[str, Any],
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log performance metrics as structured data.

    Args:
        event_type: Type of metric event (e.g., 'agent_invocation')
        metrics: Metric values (latency, duration, count, etc.)
        details: Additional context

    Example:
        ```python
        import time

        start = time.time()
        invoke_agent(message)
        duration = time.time() - start

        log_metrics('agent_invocation', {
            'duration_ms': int(duration * 1000),
            'success': True,
        }, {
            'user_id': 'user123',
            'message_id': 'msg_abc'
        })
        ```

    CloudWatch Logs Insights Query:
        ```
        fields @timestamp, eventType, duration_ms, user_id
        | filter eventType = "agent_invocation"
        | stats avg(duration_ms) as avg_duration, max(duration_ms) as max_duration
        ```
    """
    if details is None:
        details = {}

    log_entry = {
        "eventType": event_type,
        "metrics": metrics,
        **details,
    }

    logger = logging.getLogger()
    logger.info(json.dumps(log_entry))


class ObservabilityContext:
    """
    Context manager for logging operations with timing.

    Automatically logs operation start, duration, and result.

    Example:
        ```python
        with ObservabilityContext('process_message', {'user_id': 'user123'}):
            do_work()
        ```

    Logs:
        - 'process_message_started'
        - 'process_message_completed' (with duration_ms)
        - 'process_message_failed' (if exception occurs)
    """

    def __init__(self, operation_name: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize observability context.

        Args:
            operation_name: Name of the operation being monitored
            context: Additional context to include in all logs
        """
        self.operation_name = operation_name
        self.context = context or {}
        self.start_time: Optional[float] = None

    def __enter__(self):
        """Log operation start."""
        import time

        self.start_time = time.time()

        log_event(f"{self.operation_name}_started", self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log operation completion or error."""
        import time

        if self.start_time is None:
            return False

        duration_ms = int((time.time() - self.start_time) * 1000)

        if exc_type is not None:
            # Operation failed
            log_error(
                f"{self.operation_name}_failed",
                exc_val,
                {**self.context, "duration_ms": duration_ms},
            )
            return False
        else:
            # Operation succeeded
            log_metrics(
                f"{self.operation_name}_completed",
                {"duration_ms": duration_ms},
                self.context,
            )
            return False
