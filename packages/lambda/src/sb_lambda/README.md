# Lambda Functions

Lambda function code for Second Brain application stack.

## Structure

```
lambda/
├── message_handler/
│   ├── index.py              # Lambda handler for Telegram webhook
│   └── requirements.txt       # Python dependencies
└── processor/
    ├── index.py              # Lambda handler for async processing
    └── requirements.txt       # Python dependencies
```

## Building and Deploying

The CDK stack automatically:
1. Packages each Lambda directory
2. Installs Python dependencies
3. Includes shared library (`second_brain_core`)
4. Creates Lambda layers for dependencies

### Manual Testing

Test Lambda handlers locally:

```bash
# Install dependencies locally
pip install -r message_handler/requirements.txt
pip install -r processor/requirements.txt

# Add shared library to path
export PYTHONPATH=/path/to/lib/python:$PYTHONPATH

# Test message handler
python -c "from lambda.message_handler.index import lambda_handler; ..."
```

## Shared Library Integration

Both Lambdas import `second_brain_core`:

```python
from second_brain_core import Message, Task, DynamoDBClient
```

The CDK stack provides this via Lambda layer that includes `/lib/python`.

### TODO: Lambda Layer Configuration

Currently, Lambda layers are not explicitly configured in the CDK stack.

Need to:
1. Create a Lambda Layer for `second_brain_core`
2. Attach to both Lambdas in CDK code
3. Update Lambda handlers to use `/opt/python` path

See `application-stack.ts` for TODO markers.

## Environment Variables

Both Lambdas receive environment variables from CDK:

```
DYNAMODB_TABLE_NAME=second-brain
S3_BUCKET_NAME=second-brain-data
MESSAGE_QUEUE_URL=https://sqs.region.amazonaws.com/account/queue-name
AWS_REGION=us-east-1
BEDROCK_AGENT_FUNCTION_NAME=bedrock-agent-runtime  (processor only)
```

## Logging

Both Lambdas use structured logging with `observability` field for CloudWatch Logs Insights:

```python
print(json.dumps({
    'observability': 'message_received',
    'timestamp': datetime.utcnow().isoformat(),
    'user_id': user_id,
    'message_id': message_id,
}), file=sys.stderr)
```

Query in CloudWatch Logs Insights:
```
fields @timestamp, observability, user_id, message_id
| stats count() by observability
```

## TODOs in Lambda Code

### message_handler/index.py

- [ ] Validate Telegram bot token in request
- [ ] Handle message edits and deletions
- [ ] Support message attachments (photos, files)
- [ ] Rate limiting per user

### processor/index.py

- [ ] Create response queue and wire it
- [ ] Implement retry logic for agent invocation
- [ ] Handle agent errors gracefully
- [ ] Create response Lambda to send back to Telegram
- [ ] Add metrics for processing latency
- [ ] Add support for streaming agent responses
- [ ] Get actual message from DynamoDB (need to handle SK with timestamp)
- [ ] Update message status with proper SK
- [ ] Validate agent response data
- [ ] Handle duplicate task detection
- [ ] Support task dependencies
- [ ] Validate reminder times
- [ ] Create EventBridge rules for actual reminders

## Performance Considerations

### Message Handler
- Timeout: 10 seconds (should be fast)
- Memory: 256 MB
- Returns 200 immediately; processing is async

### Processor
- Timeout: 5 minutes (depends on agent)
- Memory: 512 MB
- SQS visibility timeout: 5 minutes
- SQS batch size: 1 (process one message at a time)
- SQS max concurrency: 5 (prevent overwhelming agent)

## Security

- Lambdas have least-privilege IAM roles
- S3 writes only to `raw-events/` prefix
- DynamoDB access scoped to specific table
- No hardcoded secrets (use environment variables)
- Telegram bot token should be in Secrets Manager (TODO)

## Monitoring

TODO:
- [ ] CloudWatch Logs Insights dashboard
- [ ] Custom metrics for latency
- [ ] Alarms for errors
- [ ] X-Ray traces
