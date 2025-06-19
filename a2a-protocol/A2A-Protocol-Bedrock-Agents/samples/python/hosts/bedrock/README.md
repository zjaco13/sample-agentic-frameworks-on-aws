
## Bedrock

This sample uses [Bedrock Inline Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-create-inline.html) to build a host agent that agent that coordinates user requests and delegates them to other agents via Agent-to-Agent (A2A) Protocol

## Prerequisites

- Python 3.12 or higher
- UV
- Access to a Bedrock LLM

## Running the Sample

1. Navigate to the samples directory:
    ```bash
    cd samples/python/agents/bedrock
    ```
2. Set your AWS CLI profile
3. Run an agent:
    ```bash
    uv run hosts/bedrock
    ```
5. Invoke using the [CLI client](../cli/README.md).
