"""Bedrock agents for autonomous workflows."""

from typing import Any, Dict, Optional

class Agent:
    """Base class for Bedrock agents."""

    def __init__(self, model_id: Optional[str] = None, **kwargs):
        """Initialize agent."""
        self.model_id = model_id
        self.tools = []

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent with input data."""
        raise NotImplementedError("Subclasses must implement execute()")

    def add_tool(self, tool: Any) -> None:
        """Add a tool to the agent."""
        self.tools.append(tool)


__all__ = ["Agent"]
