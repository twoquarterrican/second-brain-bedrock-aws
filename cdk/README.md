# Second Brain CDK

TypeScript AWS CDK infrastructure as code for the Second Brain application.

## Structure

```
src/
├── stacks/
│   ├── database-stack.ts   # DynamoDB tables for knowledge base
│   └── storage-stack.ts    # S3 buckets for vectors and documents
└── index.ts                # CDK App entry point

lib/                         # Compiled JavaScript (generated)
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

### Deploy Specific Stack

```bash
npm run cdk:deploy DatabaseStack
npm run cdk:deploy StorageStack
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

### DatabaseStack

Creates a DynamoDB table for the knowledge base with:
- Partition key: `id` (string)
- Sort key: `created_at` (string)
- Global secondary index on `user_id`
- Point-in-time recovery enabled
- Streams enabled for change data capture

**Outputs**:
- `SecondBrainKnowledgeTableName` - Table name
- `SecondBrainKnowledgeTableArn` - Table ARN

### StorageStack

Creates an S3 bucket for vectors and documents with:
- Versioning enabled
- Public access blocked
- Server-side encryption enabled
- SSL enforcement enabled
- Lifecycle rules (Intelligent-Tiering after 30 days)
- Auto-deletion on stack removal

**Outputs**:
- `SecondBrainVectorBucketName` - Bucket name
- `SecondBrainVectorBucketArn` - Bucket ARN

## Integration with AgentCore

The `bedrock/cdk` contains the AgentCore runtime infrastructure. To reference resources from this root CDK:

```typescript
// In bedrock/cdk/lib/stacks/agentcore-stack.ts
const knowledgeTableName = cdk.Fn.importValue('SecondBrainKnowledgeTableName');
const knowledgeTable = dynamodb.Table.fromTableName(
  this,
  'KnowledgeTable',
  knowledgeTableName
);
```

## Notes

- Stacks use `PAY_PER_REQUEST` billing for DynamoDB (suitable for variable workloads)
- S3 uses on-demand storage with Intelligent-Tiering for cost optimization
- All exports use consistent naming: `SecondBrain<Resource><Type>`
- Python CDK stubs were replaced with TypeScript for consistency with AgentCore
