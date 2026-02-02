#!/usr/bin/env python3
"""
Test script to invoke a Bedrock AgentCore runtime.

Automatically discovers the agent runtime using bedrock-agentcore-control APIs
and invokes it using bedrock-agentcore InvokeAgentRuntime.

Usage:
    test-agent [--region us-west-2]

Example:
    test-agent
    test-agent --region us-west-2
"""

import argparse
import json
import sys

import boto3


def find_agent_runtime(region: str) -> dict:
    """Find agent runtime from bedrock-agentcore-control API."""
    print("Looking up agent runtimes...")

    control = boto3.client("bedrock-agentcore-control", region_name=region)

    try:
        # List all agent runtimes
        response = control.list_agent_runtimes()

        runtimes = response.get("agentRuntimes", [])

        if not runtimes:
            print("❌ Error: No agent runtimes found")
            return None

        # Use the first runtime
        runtime = runtimes[0]

        print("✓ Found agent runtime:")
        print(f"  Name: {runtime.get('agentRuntimeName')}")
        print(f"  ARN: {runtime.get('agentRuntimeArn')}")

        if len(runtimes) > 1:
            print(f"  ({len(runtimes) - 1} other runtime(s) available)")

        return runtime

    except Exception as e:
        print(f"❌ Error querying agent runtimes: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_invoke_agent(runtime: dict, region: str):
    """Test the InvokeAgentRuntime API call."""
    agent_arn = runtime.get("agentRuntimeArn")
    print(f"\nInvoking agent runtime with ARN: {agent_arn}")

    # Use bedrock-agentcore client (NOT bedrock-agent-runtime)
    client = boto3.client("bedrock-agentcore", region_name=region)

    try:
        # Prepare payload as JSON - must have "prompt" key
        payload = json.dumps({"prompt": "Hello agent, this is a test message"}).encode("utf-8")

        response = client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn, contentType="application/json", payload=payload
        )

        print("✓ invoke_agent_runtime succeeded!")
        print("\nResponse metadata:")
        print(f"  Status Code: {response['ResponseMetadata']['HTTPStatusCode']}")

        # Read the streaming response
        print("\nAgent response:")
        try:
            # The streaming response is in the 'response' key (StreamingBody)
            stream_body = response.get("response")

            if stream_body:
                # Read the entire stream
                content = stream_body.read().decode("utf-8")
                if content:
                    print(content)
                else:
                    print("  (Empty response)")
            else:
                print("  (No response stream)")
        except Exception as e:
            print(f"  (Error reading stream: {type(e).__name__}: {e})")
            import traceback

            traceback.print_exc()

        return True

    except Exception as e:
        print("❌ invoke_agent_runtime failed:")
        print(f"  {type(e).__name__}: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Bedrock AgentCore runtime invocation")
    parser.add_argument("--region", default="us-west-2", help="AWS region")

    args = parser.parse_args()

    # Find agent runtime from bedrock-agentcore-control API
    runtime = find_agent_runtime(args.region)
    if not runtime:
        sys.exit(1)

    print(f"Region: {args.region}")

    # Test invocation
    if test_invoke_agent(runtime, args.region):
        print("\n✓ Test passed!")
        sys.exit(0)
    else:
        print("\n❌ Test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
