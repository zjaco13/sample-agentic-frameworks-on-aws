

This repository contains the code for the Deep Research Model Context Protocal Provider (MCP) server, which leverages advanced AI capabilities for deep research tasks.

## Prerequisites

- Python 3.10 or higher
- AWS CLI configured with appropriate permissions
- boto3 library
- pip package manager
- Tavily API Key
- (optional) AWS Knowledge Base ID
- (optional) AWS Guardrails ID
- (optional) AWS Guardrails Version

## Installation

### 1. Configure AWS

Before using the Deep Research MCP server, ensure your AWS CLI is properly configured with the necessary credentials and permissions:

```bash
aws configure
```

You'll need to provide:
- AWS Access Key ID
- AWS Secret Access Key
- Default region name
- Default output format (json recommended)

Ensure your AWS user has permissions for the following services:
- Amazon Bedrock
- Amazon S3
- AWS Lambda
- Amazon SageMaker (if applicable)
- AWS Guardrails
- Amazon Knowledge Bases

### 2. Install Required Libraries

Install all the required Python dependencies using pip:

```bash
pip install -r requirements.txt
```

### 3. Configure Server Parameters

Several key components need to be configured before running the server:

#### Tavily API Key

Register for a Tavily API key at [tavily.com](https://tavily.com) and set it as an environment variable:

Update the server source

```bash
tavily_client = TavilyClient(api_key="<YOUR TAVILY KEY HERE>")
```

Or add it to the `.env` file in the project root:

```
TAVILY_API_KEY=your-tavily-api-key
```

#### AWS Guardrails

If you want to enable custom guardrails based on AWS Bedrock Guardrails, update the source flag to "true"

```
#set to true if you want to use custom AWS Guardrails
USE_GUARDRAILS = "false"
```

and onfigure AWS Guardrails by editing the following code:

```
guardrail_id = "<YOUR GUARDRAIL ID HERE>"
guardrail_version = "<YOUR GUARDRAIL VERSION HERE>"
```

Refer to the AWS documentation on how to create and configure your Guardrails.

#### AWS Knowledge Bases

Set up your knowledge bases in the `config/knowledge_bases.json` file:

```json
{
  "kb_list": [
    {
      "kb_id": "your-knowledge-base-id-1",
      "region": "your-aws-region",
      "description": "Knowledge Base 1 Description"
    },
    {
      "kb_id": "your-knowledge-base-id-2",
      "region": "your-aws-region",
      "description": "Knowledge Base 2 Description"
    }
  ],
  "default_kb_id": "your-knowledge-base-id-1"
}
```

## Usage

After completing the installation and configuration steps, you can start the server with:

```bash
python src/main.py
```

By default, the server will be accessible at http://localhost:8000.

## Advanced Configuration

For advanced configurations or customization options, please refer to the `config/server_config.json` file.

## Troubleshooting

If you encounter any issues:

1. Verify your AWS credentials are properly configured
2. Ensure all API keys are correctly set
3. Check the logs in the `logs/` directory for detailed error messages
4. Verify your Python version meets the minimum requirement (3.10+)

## License



## Contributing

