"""Observability utilities for structured logging in CloudWatch.

Provides helpers for emitting structured logs that are easy to query
in CloudWatch Logs Insights.

Example:
    ```python
    from sb_shared import log_event

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

import copy
import functools
import json
import logging
from typing import Any, Callable, Dict, Literal, Optional

# Initialize AWS Lambda logging
try:
    import aws_lambda_logging

    HAS_LAMBDA_LOGGING = True
except ImportError:
    HAS_LAMBDA_LOGGING = False

# Thread-local storage for AWS request ID
import threading

_request_id_storage = threading.local()


def set_aws_request_id(request_id: str) -> None:
    """Store the AWS request ID for use in all logs."""
    _request_id_storage.request_id = request_id


def get_aws_request_id() -> Optional[str]:
    """Get the current AWS request ID."""
    return getattr(_request_id_storage, "request_id", None)


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
        fields @timestamp, eventType, awsRequestId, user_id, task_id, category
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

    # Include AWS request ID if available
    request_id = get_aws_request_id()
    if request_id:
        log_entry["awsRequestId"] = request_id

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


def lambda_handler(
    kind: Literal["function_url", "sqs", "s3", "dynamodb"] = "function_url",
) -> Callable:
    """
    Decorator for Lambda handlers that sets up logging and handles event redaction.

    Args:
        kind: Type of Lambda event ('function_url', 'sqs', 's3', 'dynamodb')

    Example:
        ```python
        @lambda_handler(kind="function_url")
        def handler(event, context):
            return {"statusCode": 200}
        ```

    The decorator:
    - Calls setup_logging()
    - Extracts and stores AWS request ID from context
    - Logs the incoming event (with sensitive fields redacted)
    - Catches and logs exceptions
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(event, context):
            # Setup logging
            setup_logging()

            # Store AWS request ID for use in all logs
            set_aws_request_id(context.aws_request_id)

            # Prepare event for logging (redact sensitive fields)
            event_to_log = _redact_event(event, kind)

            # Log incoming event
            log_event(
                f"handler_invoked_{kind}",
                {
                    "handlerKind": kind,
                    "event": event_to_log,
                },
            )

            try:
                # Call the actual handler
                result = func(event, context)
                return result

            except Exception as e:
                # Log error with AWS request ID
                log_error(
                    f"handler_error_{kind}",
                    e,
                    {
                        "handlerKind": kind,
                        "awsRequestId": context.aws_request_id,
                    },
                )
                raise

        return wrapper

    return decorator


def _redact_event(event: Any, kind: str) -> Any:
    """
    Redact sensitive fields from Lambda event based on handler kind.

    Args:
        event: The Lambda event
        kind: Type of Lambda event

    Returns:
        Event with sensitive fields redacted
    """
    # Make a deep copy to avoid modifying the original
    redacted = copy.deepcopy(event)

    if kind == "function_url":
        # For Function URL events, redact headers that might contain auth tokens
        if isinstance(redacted, dict) and "headers" in redacted:
            headers_to_redact = [
                "authorization",
                "x-api-key",
                "x-telegram-bot-api-secret-token",
            ]
            for header in headers_to_redact:
                if header in redacted["headers"]:
                    redacted["headers"][header] = "***REDACTED***"
        # Redact body if it contains sensitive data (truncate for size)
        if isinstance(redacted, dict) and "body" in redacted:
            if isinstance(redacted["body"], str) and len(redacted["body"]) > 500:
                redacted["body"] = redacted["body"][:500] + "...[truncated]"

    elif kind == "sqs":
        # For SQS, log the whole event for now (no redaction needed typically)
        pass

    elif kind == "s3":
        # For S3, redact object content but keep metadata
        if isinstance(redacted, dict) and "Records" in redacted:
            for record in redacted.get("Records", []):
                if "body" in record:
                    record["body"] = "***REDACTED***"

    elif kind == "dynamodb":
        # For DynamoDB Streams, redact sensitive attributes
        if isinstance(redacted, dict) and "Records" in redacted:
            for record in redacted.get("Records", []):
                if "dynamodb" in record and "NewImage" in record["dynamodb"]:
                    # You could redact specific attributes here
                    pass

    return redacted


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
