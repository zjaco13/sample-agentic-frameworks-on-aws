## CLI

The CLI is a  host application that demonstrates the capabilities of an A2AClient. It supports reading a server's AgentCard and text-based collaboration with a remote agent. All content received from the A2A server is printed to the console. 

The client will use streaming if the server supports it.

## Prerequisites

- Python 3.13 or higher
- UV
- A running A2A server

## Running the CLI

1. Navigate to the samples directory:
    ```bash
    cd samples/python
    ```
2. Run the example client
    ```
    uv run hosts/cli/run_from_local_client.py
    ```

 This will prompt the user for a query. Type questions related to websearch like 'who is ceo of Amazon?' to route them to the web search agent, or enter queries like 'convert 1 USD to EUR' to route them to the currency converter agent
