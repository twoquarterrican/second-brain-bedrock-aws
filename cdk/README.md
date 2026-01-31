# Second Brain CDK

TypeScript AWS CDK infrastructure as code for the Second Brain application.

## Structure

```
src/
├── stacks/
│   ├── application-stack.ts   # Single stack with all resources
│   └── index.ts               # Stack exports
└── index.ts                   # CDK App entry point

lambda/
├── message_handler/           # Telegram webhook Lambda
│   ├── index.py
│   └── requirements.txt
├── processor/                 # Async message processor Lambda
│   ├── index.py
│   └── requirements.txt
└── README.md                  # Lambda documentation

lib/                           # Compiled JavaScript (generated)
```

## Setup

### Prerequisites

- Node.js 18+ ([nvm](https://github.com/nvm-sh/nvm) recommended)
- AWS credentials configured

### Install Dependencies

```bash
npm install
```

## Development

### Build TypeScript

```bash
npm run build
```

### Watch Mode

```bash
npm run watch
```

## Deployment

### Synthesize CloudFormation

```bash
npm run cdk:synth
```

### Deploy All Stacks

```bash
npm run cdk:deploy
```

### Preview Changes

```bash
npm run cdk:diff
```

### Destroy Stacks

```bash
npm run cdk:destroy
```

## Stacks

### ApplicationStack

Single stack containing all core infrastructure:

**Data Layer**:
- DynamoDB table: `second-brain`
  - Partition key: `PK` (e.g., `user#<user_id>`)
  - Sort key: `SK` (type-specific, e.g., `task#<id>`, `message#<timestamp>#<id>`)
  - Point-in-time recovery enabled
  - Streams enabled for CDC
  - Pay-per-request billing

- S3 bucket: `second-brain-data`
  - Prefixes: `raw-events/`, `vector-embeddings/`, `backups/`
  - Versioning enabled
  - Server-side encryption
  - Intelligent-Tiering after 30 days
  - Public access blocked

**API Layer**:
- Lambda Function URL for Telegram webhook (message handler)
  - Entry point for incoming messages
  - Saves raw to S3, metadata to DynamoDB
  - Returns 200 OK immediately

**Async Processing Layer**:
- SQS Queue: `second-brain-messages`
  - Decouples webhook from processing
  - Enables retries and batching

- Processing Lambda
  - Triggered by SQS messages
  - Invokes Bedrock agent
  - Creates tasks/reminders in DynamoDB

**IAM Roles & Policies**:
- Message handler role: DynamoDB write, S3 write (raw-events), SQS send
- Processing role: DynamoDB read/write, S3 read (raw-events), SQS consume, Lambda invoke

**Outputs**:
- `SecondBrainDataTableName` - Main data table
- `SecondBrainDataBucketName` - Data storage bucket
- `SecondBrainMessageQueueUrl` - Processing queue
- `SecondBrainWebhookUrl` - Telegram webhook URL

## Lambda Functions

Lambda code in `lambda/` directory:

### message_handler/
- Entry point for Telegram webhook
- Saves raw messages to S3 (immutable)
- Stores metadata in DynamoDB
- Queues for async processing
- Returns 200 immediately

### processor/
- Triggered by SQS messages
- Gets message from DynamoDB
- Invokes Bedrock agent
- Creates tasks/reminders/todos
- Queues response for delivery

**See `lambda/README.md` for details and TODOs.**

## Shared Library Integration

Both Lambdas use `second_brain_core` from `/lib/python/`:
```python
from second_brain_core import Message, Task, DynamoDBClient
```

The CDK stack packages this as a Lambda layer (TODO: explicit layer configuration).

## Integration with AgentCore

The `bedrock/cdk` contains the AgentCore runtime infrastructure. To reference resources from this root CDK:

```typescript
// In bedrock/cdk/lib/stacks/agentcore-stack.ts
const dataTableName = cdk.Fn.importValue('SecondBrainDataTableName');
const dataTable = dynamodb.Table.fromTableName(
  this,
  'DataTable',
  dataTableName
);
```

## Environment Variables

Lambda functions receive these from CDK:
```
DYNAMODB_TABLE_NAME=second-brain
S3_BUCKET_NAME=second-brain-data
MESSAGE_QUEUE_URL=<SQS queue URL>
BEDROCK_AGENT_FUNCTION_NAME=bedrock-agent-runtime
AWS_REGION=<region>
```

## Notes

- Single ApplicationStack for simplicity and unified resource management
- DynamoDB uses `PAY_PER_REQUEST` billing (suitable for variable workloads)
- S3 uses Intelligent-Tiering for cost optimization
- All exports use consistent naming: `SecondBrain<Resource>`
- TypeScript CDK for consistency with AgentCore and AWS best practices
- Python Lambda code for agent and data integration
- Structured logging with `observability` field for CloudWatch Logs Insights

## TODOs

See comments in `application-stack.ts` and `lambda/README.md` for implementation gaps:

- [ ] Lambda layers for dependencies
- [ ] Bedrock agent Lambda invocation permissions
- [ ] Response queue and handler Lambda
- [ ] CloudWatch Logs Insights dashboard
- [ ] Custom metrics and alarms
- [ ] Telegram message validation
- [ ] Error handling and retry logic
