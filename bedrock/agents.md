# Bedrock Agents

This directory contains agent definitions for autonomous workflows in the Second Brain system.

## Architecture

Agents are autonomous systems that use Bedrock Claude to perform complex tasks with reasoning, tool use, and planning capabilities.

## Agent Types

### Knowledge Ingestion Agent

**Purpose**: Automatically ingest and process documents into the knowledge base

**Capabilities**:
- Detect document type and format
- Extract text from various formats (PDF, DOCX, MD, TXT)
- Chunk content into semantic units
- Generate embeddings
- Store in DynamoDB and S3

**Tools Available**:
- S3 Upload
- DynamoDB Write
- Text Extraction Lambda
- Bedrock Embeddings API

### Knowledge Synthesis Agent

**Purpose**: Generate insights by connecting related information

**Capabilities**:
- Search across knowledge base
- Identify connections between concepts
- Synthesize summaries
- Generate new insights
- Suggest related topics

**Tools Available**:
- Vector Search API
- DynamoDB Query
- Bedrock Claude Inference
- Knowledge Graph API

### Query Response Agent

**Purpose**: Answer user questions with context-aware responses

**Capabilities**:
- Process user queries
- Retrieve relevant context
- Synthesize information
- Generate explanations
- Provide source citations

**Tools Available**:
- Vector Search API
- DynamoDB Query
- Web Search (optional)
- Bedrock Claude Inference

## Implementation

Each agent is implemented as:

```python
from bedrock.agents.base import Agent

class MyAgent(Agent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tools = [...]

    def execute(self, input_data: dict) -> dict:
        # Agent logic here
        pass
```

## Configuration

Agents are configured via environment variables and configuration files:

```env
AGENT_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AGENT_MAX_ITERATIONS=10
AGENT_TIMEOUT=300
```

## Monitoring

Agent execution is monitored via:
- CloudWatch Logs
- X-Ray Tracing
- Custom Metrics

## Future Agents

- [ ] Fact Checking Agent
- [ ] Document Summarization Agent
- [ ] Concept Mapper Agent
- [ ] Anomaly Detection Agent
- [ ] Trend Analysis Agent
