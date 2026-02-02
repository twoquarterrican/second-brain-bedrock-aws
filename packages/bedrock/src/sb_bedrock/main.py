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
def classify_message(message: str) -> dict:
    """
    Classify a message by topic/category.

    Args:
        message: The message text to classify

    Returns:
        Dictionary with classification results including category and confidence
    """
    # Stub implementation
    log.info(f"Classifying message: {message[:100]}...")
    return {
        "category": "general",
        "confidence": 0.8,
        "topics": ["general"],
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


# Simple math tool for reference
@tool
def add_numbers(a: int, b: int) -> int:
    """Return the sum of two numbers"""
    return a + b


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
                You are a knowledge management assistant. Your role is to:
                1. Classify incoming messages by topic/category
                2. Search for similar existing messages
                3. Create or update messages in the knowledge base
                4. Communicate with the user about actions taken

                Always use the available tools to classify, search, and store messages.
                Be thorough in categorizing and finding relationships between messages.

                IMPORTANT: Always use the respond_to_user tool to:
                - Summarize the actions you took (classified as X, found Y similar messages, etc.)
                - Ask clarifying questions if needed
                - Confirm the message was saved

                Do NOT return long responses. Keep summaries concise and use the tool
                to communicate with the user.
            """,
            tools=[
                classify_message,
                find_similar_messages,
                upsert_message,
                respond_to_user,
                code_interpreter.code_interpreter,
                add_numbers,
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
