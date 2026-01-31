# Claude Project Instructions

## Project Overview

This is the **Second Brain** project - a distributed knowledge management system powered by AWS Bedrock, DynamoDB, S3, Lambda, and API Gateway.

## Project Structure

```
second-brain-bedrock-aws/
├── bedrock/                    # Bedrock agent applications
│   ├── src/                   # Agent runtime code
│   │   ├── main.py           # Agent entry point
│   │   ├── mcp_client/       # MCP client for tools
│   │   └── model/            # Agent models
│   ├── cdk/                   # AgentCore infrastructure (TypeScript)
│   │   ├── bin/
│   │   ├── lib/
│   │   └── package.json
│   ├── mcp/                   # MCP tools (Lambda functions)
│   ├── test/                  # Agent tests
│   └── pyproject.toml
├── cdk/                       # Root shared infrastructure (TypeScript)
│   ├── src/
│   │   ├── stacks/           # DynamoDB, S3, etc.
│   │   └── index.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── cdk.json
├── scripts/                   # Python utility scripts
│   ├── deploy.py
│   └── utils.py
├── tests/                     # Python tests
├── pyproject.toml             # Root Python configuration
├── README.md                  # Project documentation
└── claude.md                  # This file
```

## Technology Stack

- **Python 3.10+** with `uv` package manager (for Bedrock agent)
- **Node.js 18+** with npm (for TypeScript CDK)
- **TypeScript** - CDK infrastructure as code
- **AWS Services**: Bedrock, DynamoDB, S3, Lambda, API Gateway, AgentCore, CloudWatch, X-Ray
- **LLM**: Claude (via Bedrock AgentCore)
- **Testing**: pytest (Python), Jest (TypeScript)
- **Code Quality**: black, ruff, mypy (Python)

## Development Workflow

### Setup

```bash
# Python dependencies
uv sync --with bedrock --with dev

# CDK dependencies
cd cdk && npm install && cd ..
```

### Common Commands

#### Python

```bash
# Run Python scripts
uv run scripts/deploy.py

# Run Python tests
uv run pytest tests/ -v

# Format Python code
uv run black .

# Lint Python code
uv run ruff check . --fix

# Type check Python code
uv run mypy bedrock/ scripts/
```

#### TypeScript CDK

```bash
cd cdk

# Build
npm run build

# Watch mode
npm run watch

# Synthesize CloudFormation
npm run cdk:synth

# Deploy infrastructure
npm run cdk:deploy

# Preview changes
npm run cdk:diff

# Destroy stacks
npm run cdk:destroy
```

## Module Responsibilities

### bedrock/

**AgentCore deployment** - Production-ready Bedrock agent application

**Key Directories**:
- `src/` - Agent runtime code (Python)
- `cdk/` - AgentCore infrastructure (TypeScript)
- `mcp/` - MCP tools for agent capabilities
- `test/` - Agent tests

### cdk/

**Shared infrastructure** - Root CDK for DynamoDB, S3, and other shared AWS resources

**Key Directories**:
- `src/stacks/` - CDK stack definitions (TypeScript)
  - `database-stack.ts` - DynamoDB tables
  - `storage-stack.ts` - S3 buckets
- `src/index.ts` - CDK app entry point

**Integration**: AgentCore can reference outputs from root CDK stacks via cross-stack references.

### scripts/

**Python utilities** - Deployment and operational scripts

**Key Files**:
- `deploy.py` - Deployment orchestration
- `utils.py` - AWS client helpers

## Dependency Management

### Python (`uv`)

Dependency groups for Python isolation:

- **dev**: Development tools (pytest, black, ruff, mypy, pre-commit, bedrock-agentcore, strands-agents)
- **bedrock**: Bedrock/LangChain libraries

Install specific groups:
```bash
uv sync --with bedrock --with dev
```

### TypeScript (npm)

Node.js dependencies in `cdk/package.json`:

- `aws-cdk-lib` - AWS CDK library
- `constructs` - CDK constructs framework
- `typescript` - TypeScript compiler

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
