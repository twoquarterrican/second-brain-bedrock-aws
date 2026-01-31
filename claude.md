# Claude Project Instructions

## Project Overview

This is the **Second Brain** project - a distributed knowledge management system powered by AWS Bedrock, DynamoDB, S3, Lambda, and API Gateway.

## Project Structure

```
second-brain-bedrock-aws/
├── bedrock/              # Bedrock LLM applications
│   ├── agents.md        # Agent definitions
│   ├── __init__.py
│   └── app.py
├── cdk/                 # AWS CDK infrastructure
│   ├── __init__.py
│   └── app.py
├── scripts/             # Deployment and utility scripts
│   ├── deploy.py
│   └── utils.py
├── tests/               # Test suite
├── pyproject.toml       # Project configuration
├── README.md            # Project documentation
└── claude.md            # This file
```

## Technology Stack

- **Python 3.9+** with `uv` package manager
- **AWS Services**: Bedrock, DynamoDB, S3, Lambda, API Gateway, CloudWatch, X-Ray
- **LLM**: Claude (via Bedrock)
- **Infrastructure**: AWS CDK
- **Testing**: pytest
- **Code Quality**: black, ruff, mypy

## Development Workflow

### Setup

```bash
uv sync --with bedrock --with cdk --with dev
```

### Common Commands

```bash
# Run scripts
uv run scripts/deploy.py

# Run tests
uv run pytest tests/ -v

# Format code
uv run black .

# Lint code
uv run ruff check . --fix

# Type check
uv run mypy bedrock/ cdk/ scripts/

# Deploy infrastructure
uv run cdk deploy
```

## Module Responsibilities

### bedrock/

- LLM integrations using Bedrock Claude
- Agent definitions for autonomous workflows
- Embedding generation
- Model invocation wrappers

**Key Files**:
- `app.py` - Main Bedrock application class
- `agents.md` - Agent architecture documentation

### cdk/

- Infrastructure as Code for AWS services
- Stack definitions for DynamoDB, S3, Lambda, API Gateway
- IAM roles and policies
- Environment-specific configurations

**Key Files**:
- `app.py` - CDK app entry point with stack definitions

### scripts/

- Deployment automation
- Utility functions for AWS service interactions
- Database migrations
- Data processing scripts

**Key Files**:
- `deploy.py` - Deployment orchestration
- `utils.py` - Common AWS client helpers

## Dependency Management

Using `uv` with dependency groups:

- **dev**: Testing, linting, formatting tools
- **bedrock**: Bedrock-specific libraries (langchain, document processing)
- **cdk**: AWS CDK libraries

Install specific groups:
```bash
uv sync --with bedrock --with cdk --with dev
```

## Code Standards

- **Formatting**: Use `black` (line length: 100)
- **Linting**: Use `ruff` (E, F, W rules)
- **Type Checking**: Use `mypy` with basic checking
- **Testing**: pytest with test files in `tests/`

Run all checks:
```bash
uv run black . && uv run ruff check . --fix && uv run mypy bedrock/ cdk/ scripts/
```

## Configuration

Configuration via environment variables (`.env` file):

```env
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
DYNAMODB_TABLE_NAME=second-brain-knowledge
S3_BUCKET_NAME=second-brain-vectors
ENVIRONMENT=dev
```

## Key Concepts

### Knowledge Ingestion
Documents are uploaded, processed, embedded, and stored in DynamoDB/S3 for semantic search.

### Vector Search
User queries are embedded and matched against stored document embeddings for context retrieval.

### Agentic Workflows
Claude agents autonomously perform complex tasks using tools and reasoning capabilities.

### Infrastructure as Code
All AWS infrastructure is defined in CDK for reproducible, version-controlled deployments.

## Adding New Features

1. **New Bedrock Agent**: Create in `bedrock/agents/`
2. **New Infrastructure**: Add CDK constructs to `cdk/stacks/`
3. **New Utility Scripts**: Add to `scripts/`
4. **New Dependencies**: Update `pyproject.toml` with appropriate group

## Testing

All new code should include tests in `tests/`:

```bash
uv run pytest tests/ -v
```

## Deployment

```bash
# Deploy infrastructure
uv run cdk deploy

# Or use deployment script
uv run scripts/deploy.py --environment production
```

## Monitoring & Debugging

- **CloudWatch Logs**: Monitor application and Lambda logs
- **X-Ray**: Trace distributed requests
- **CloudWatch Metrics**: Custom application metrics
- **AWS Console**: Real-time resource monitoring

## Future Enhancements

- Multi-user workspaces
- Real-time collaboration
- Custom model fine-tuning
- Advanced knowledge graph visualization
- Mobile client support

## Resources

- [AWS Bedrock Docs](https://docs.aws.amazon.com/bedrock/)
- [AWS CDK Docs](https://docs.aws.amazon.com/cdk/)
- [boto3 Docs](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Claude API Docs](https://docs.anthropic.com/claude/)

## Support

For questions or issues, refer to the main README.md or open an issue in the repository.
