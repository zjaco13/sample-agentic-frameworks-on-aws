
## Bedrock

This sample uses [Bedrock Inline Agents](https://langchain-ai.github.io/langgraph/) to build a simple web and wikipedia agent and host it as an A2A server.

## Prerequisites

- Python 3.12 or higher
- UV
- Access to a Bedrock LLM and Tavily API Key

## Running the Sample

1. Navigate to the samples directory:
    ```bash
    cd samples/python
    ```
2. Set your AWS CLI profile
3. Create a file named .env under agents/websearchagent. 
    ```bash
    touch agents/websearchagent/.env
    ```
4. Add `TAVILY_API_KEY` to .env 
5. Run an agent:
    ```bash
    uv run agents/websearchagent
    ```
6. Invoke with a `POST` (Optional Testing)

### POST

Send a `POST` request to `http://localhost:10000` with this body:

```
{
  "jsonrpc": "2.0",
  "id": 11,
  "method": "tasks/send",
  "params": {
    "id": "129",
    "sessionId": "8f01f3d172cd4396a0e535ae8aec6687",
    "acceptedOutputModes": [
      "text"
    ],
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "Tell me about the Cinco de Mayo holiday"
        }
      ]
    }
  }
}
```