import os

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import (
    AgentCoreMemoryConfig,
    RetrievalConfig,
)
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from strands import Agent, tool
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

from .model.load import load_model

MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION")

if os.getenv("LOCAL_DEV") == "1":
    # In local dev, instantiate dummy MCP client so the code runs without deploying
    from contextlib import nullcontext
    from types import SimpleNamespace

    strands_mcp_client = nullcontext(SimpleNamespace(list_tools_sync=lambda: []))
else:
    # Not ready for gateway mcp yet
    from contextlib import nullcontext
    from types import SimpleNamespace

    # todo: Import AgentCore Gateway as Streamable HTTP MCP Client
    # todo: strands_mcp_client = get_streamable_http_mcp_client()
    strands_mcp_client = nullcontext(SimpleNamespace(list_tools_sync=lambda: []))


# Define tools for message processing
@tool
def classify_and_extract(
    message: str,
    type: str,  # task, reminder, or todo
    title: str | None = None,
    description: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
    scheduled_for: str | None = None,
    recurrence: str | None = None,
    order: int | None = None,
) -> dict:
    """
    Classify a message and extract structured fields based on type.

    Args:
        message: The original message text
        type: Message type - 'task', 'reminder', or 'todo'

        For type='task':
            title: Task title (required)
            description: Task description
            due_date: ISO format date (YYYY-MM-DD)
            priority: low, medium, high

        For type='reminder':
            title: Reminder title (required)
            scheduled_for: ISO format datetime (YYYY-MM-DDTHH:MM:SSZ)
            recurrence: once, daily, weekly, monthly

        For type='todo':
            title: Todo text (required)
            order: Position in list

    Returns:
        Dictionary with extracted fields and status
    """
    log.info(f"Classifying as {type}: {message[:100]}...")

    # Basic validation
    if type not in ["task", "reminder", "todo"]:
        return {"error": f"Invalid type: {type}. Must be task, reminder, or todo"}

    if not title:
        return {"error": f"title is required for type '{type}'"}

    return {
        "type": type,
        "title": title,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "scheduled_for": scheduled_for,
        "recurrence": recurrence,
        "order": order,
        "status": "classified",
    }


@tool
def find_similar_messages(message: str, user_id: str, limit: int = 5) -> list:
    """
    Find similar existing messages for the user.

    Args:
        message: The message to find similar matches for
        user_id: User ID to search within
        limit: Maximum number of results to return

    Returns:
        List of similar messages with similarity scores
    """
    # Stub implementation
    log.info(f"Finding similar messages for user {user_id}")
    return [
        {
            "message_id": "msg-123",
            "content": "Similar message example",
            "similarity_score": 0.85,
            "timestamp": "2025-02-01T00:00:00Z",
        }
    ]


@tool
def upsert_message(message_id: str, user_id: str, content: str, category: str) -> dict:
    """
    Create or update a message in the knowledge base.

    Args:
        message_id: Unique message ID
        user_id: User ID
        content: Message content
        category: Message category/classification

    Returns:
        Dictionary with operation result (created=True/False, message_id)
    """
    # Stub implementation
    log.info(f"Upserting message {message_id} for user {user_id}")
    return {
        "message_id": message_id,
        "user_id": user_id,
        "created": True,
        "category": category,
        "timestamp": "2025-02-01T00:00:00Z",
    }


@tool
def respond_to_user(user_id: str, message: str) -> dict:
    """
    Send a response back to the user summarizing actions taken or asking for follow-up.

    Args:
        user_id: User ID to send response to
        message: Response message for the user (summary, confirmation, or follow-up question)

    Returns:
        Dictionary with response delivery status
    """
    # Stub implementation - will queue message to Telegram/response channel
    log.info(f"Responding to user {user_id}: {message[:100]}...")
    return {
        "user_id": user_id,
        "message_sent": True,
        "timestamp": "2025-02-01T00:00:00Z",
    }


# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()
log = app.logger


@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(context, "session_id", "default")

    # Configure memory if available
    session_manager = None
    if MEMORY_ID:
        session_manager = AgentCoreMemorySessionManager(
            AgentCoreMemoryConfig(
                memory_id=MEMORY_ID,
                session_id=session_id,
                actor_id="quickstart-user",
                retrieval_config={
                    "/users/quickstart-user/facts": RetrievalConfig(top_k=3, relevance_score=0.5),
                    "/users/quickstart-user/preferences": RetrievalConfig(
                        top_k=3, relevance_score=0.5
                    ),
                },
            ),
            REGION,
        )
    else:
        log.warning("MEMORY_ID is not set. Skipping memory session manager initialization.")

    # Create code interpreter
    code_interpreter = AgentCoreCodeInterpreter(
        region=REGION, session_name=session_id, auto_create=True, persist_sessions=True
    )

    with strands_mcp_client as client:
        # Get MCP Tools
        tools = client.list_tools_sync()

        # Create agent
        agent = Agent(
            model=load_model(),
            session_manager=session_manager,
            system_prompt="""
                You are a knowledge management assistant. Your role is to process user messages and organize them into your knowledge base.

                CLASSIFICATION TASK:
                Analyze each message and determine what type it represents:
                - 'task': Something that needs to be done (has a goal, priority, due date)
                - 'reminder': A notification or event to be reminded about (has a scheduled time, optional recurrence)
                - 'todo': A simple item in a todo list (lightweight, ordered)

                WORKFLOW:
                1. Use classify_and_extract tool to classify the message and extract relevant fields based on type
                   - For tasks: extract title, description, due_date (if mentioned), priority
                   - For reminders: extract title, scheduled_for time, recurrence pattern
                   - For todos: extract title, order position

                2. Use find_similar_messages to find related existing messages for context

                3. Use upsert_message to save the classified message

                4. Use respond_to_user to summarize what you did

                IMPORTANT GUIDELINES:
                - Always extract specific fields for the chosen type
                - If a field is not mentioned or unclear, leave it as None
                - Be conservative with classifications - if unsure, ask the user
                - Keep responses concise when using respond_to_user
            """,
            tools=[
                classify_and_extract,
                find_similar_messages,
                upsert_message,
                respond_to_user,
                code_interpreter.code_interpreter,
            ]
            + tools,
        )

        # Execute and format response
        stream = agent.stream_async(payload.get("prompt"))

        async for event in stream:
            # Handle Text parts of the response
            if "data" in event and isinstance(event["data"], str):
                yield event["data"]

            # Implement additional handling for other events
            # if "toolUse" in event:
            #   # Process toolUse

            # Handle end of stream
            # if "result" in event:
            #    yield(format_response(event["result"]))


def format_response(result) -> str:
    """Extract code from metrics and format with LLM response."""
    parts = []

    # Extract executed code from metrics
    try:
        tool_metrics = result.metrics.tool_metrics.get("code_interpreter")
        if tool_metrics and hasattr(tool_metrics, "tool"):
            action = tool_metrics.tool["input"]["code_interpreter_input"]["action"]
            if "code" in action:
                parts.append(
                    f"## Executed Code:\n```{action.get('language', 'python')}\n{action['code']}\n```\n---\n"
                )
    except (AttributeError, KeyError):
        pass  # No code to extract

    # Add LLM response
    parts.append(f"## 📊 Result:\n{str(result)}")
    return "\n".join(parts)


if __name__ == "__main__":
    app.run()
