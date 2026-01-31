# Second Brain - Bedrock AWS

A distributed knowledge management system powered by AWS Bedrock, designed to augment human cognition through semantic search, intelligent synthesis, and context-aware information retrieval.

## Overview

This project implements a "second brain" - a personal knowledge management system that captures, organizes, and intelligently retrieves information using:

- **AWS Bedrock** - Large Language Models for embeddings and semantic understanding
- **DynamoDB** - NoSQL database for metadata and knowledge graph storage
- **S3 with Vector Indexes** - Scalable storage for documents with vector embeddings
- **Lambda** - Serverless compute for processing and orchestration
- **API Gateway** - RESTful API for client access
- **CloudWatch & X-Ray** - Observability and performance monitoring

## Features

- **Semantic Search** - Find related information using vector embeddings instead of keyword matching
- **Intelligent Synthesis** - Generate summaries and connections across knowledge domains
- **Multi-source Ingestion** - Process documents, notes, and structured data
- **Context-aware Retrieval** - Surface relevant information based on your current context
- **Scalable Architecture** - Leverage AWS managed services for automatic scaling

## Project Structure

```
.
├── bedrock/              # AWS Bedrock applications and deployments
│   ├── src/             # Bedrock agent runtime code
│   ├── cdk/             # CDK for AgentCore infrastructure (TypeScript)
│   ├── mcp/             # MCP tools for agent capabilities
│   └── main.py          # Agent entry point
├── cdk/                  # Root AWS CDK infrastructure (TypeScript)
│   ├── src/
│   │   ├── stacks/      # CDK stack definitions
│   │   └── index.ts     # CDK app entry point
│   ├── package.json     # Node.js dependencies
│   └── tsconfig.json    # TypeScript configuration
├── scripts/              # Python utility scripts
│   ├── deploy.py        # Deployment automation
│   └── utils.py         # AWS client helpers
├── tests/                # Python test suite
├── pyproject.toml        # Python project configuration
└── README.md             # This file
```

## Getting Started

### Prerequisites

- Python 3.10+ (for Bedrock/AgentCore)
- Node.js 18+ (for CDK) - [nvm](https://github.com/nvm-sh/nvm) recommended
- `uv` package manager
- AWS Account with appropriate permissions
- AWS CLI configured

### Installation

#### Python Dependencies

```bash
# Install Python dependencies
uv sync

# Install with specific dependency groups
uv sync --with bedrock --with dev
```

#### CDK Dependencies

```bash
# Install CDK dependencies
cd cdk
npm install
cd ..
```

### Configuration

Create a `.env` file in the project root:

```env
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
DYNAMODB_TABLE_NAME=second-brain-knowledge
S3_BUCKET_NAME=second-brain-vectors
```

### Running Scripts

#### Python Scripts

All Python scripts are run using `uv run`:

```bash
# Deploy infrastructure
uv run scripts/deploy.py

# Run tests
uv run pytest tests/

# Format code
uv run black .

# Lint code
uv run ruff check .
```

#### CDK Commands

```bash
cd cdk

# Build TypeScript
npm run build

# Watch mode (rebuild on changes)
npm run watch

# Synthesize CloudFormation
npm run cdk:synth

# Deploy all stacks
npm run cdk:deploy

# Deploy specific stack
npm run cdk:deploy DatabaseStack

# Preview changes
npm run cdk:diff

# Destroy stacks
npm run cdk:destroy
```

## Python Dependency Groups

The project uses `uv` dependency groups for Python isolation:

- **dev** - Development tools (pytest, black, ruff, mypy, pre-commit, bedrock-agentcore)
- **bedrock** - Bedrock/LangChain libraries (langchain, document processors)

Install specific groups:

```bash
uv sync --with bedrock --with dev
```

## Architecture

### Knowledge Ingestion Pipeline

1. Document Upload → S3
2. Text Extraction & Chunking → Lambda
3. Embedding Generation → Bedrock Claude
4. Vector Storage → S3 Vectors
5. Metadata → DynamoDB

### Query Pipeline

1. User Query → API Gateway
2. Query Embedding → Bedrock Claude
3. Vector Search → S3 Vectors
4. Metadata Retrieval → DynamoDB
5. Synthesis → Bedrock Claude
6. Response → API Gateway → Client

## Development

### Running Tests

```bash
uv run pytest tests/ -v
```

### Code Quality

```bash
# Format
uv run black .

# Lint
uv run ruff check . --fix

# Type checking
uv run mypy bedrock/ cdk/ scripts/
```

### Pre-commit Hooks

Install pre-commit hooks:

```bash
uv run pre-commit install
```

## Deployment

### CDK Deployment

```bash
uv run cdk deploy
```

### Manual Deployment

```bash
uv run scripts/deploy.py --environment production
```

## AWS Services Used

| Service | Purpose |
|---------|---------|
| **Bedrock** | LLM embeddings and inference |
| **DynamoDB** | Metadata and relationship storage |
| **S3** | Document and vector storage |
| **Lambda** | Processing and orchestration |
| **API Gateway** | REST API interface |
| **CloudWatch** | Logging and monitoring |
| **X-Ray** | Distributed tracing |
| **IAM** | Access control |

## Contributing

1. Create a feature branch
2. Make changes in the appropriate module
3. Run tests and linting
4. Submit a pull request

## Security

- Use IAM roles for AWS service authentication
- Encrypt sensitive data at rest and in transit
- Validate and sanitize all user inputs
- Use VPC endpoints for private AWS service access

## Cost Optimization

- Leverage DynamoDB on-demand billing for variable workloads
- Use S3 Intelligent-Tiering for storage cost reduction
- Implement request batching to reduce API calls
- Use Lambda provisioned concurrency only when needed

## Future Enhancements

- [ ] Real-time collaboration features
- [ ] Custom model fine-tuning
- [ ] Advanced knowledge graph visualization
- [ ] Mobile application support
- [ ] Multi-user workspaces

## License

MIT

## Support

For issues and feature requests, please open an issue in the repository.
