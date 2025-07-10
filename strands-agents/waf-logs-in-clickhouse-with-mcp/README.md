# WAF Logs Analysis with ClickHouse and MCP

An intelligent agent system for analyzing AWS WAF (Web Application Firewall) logs stored in ClickHouse database using Strands Agents framework and Model Context Protocol (MCP).

## Overview

This project provides a natural language interface to query and analyze AWS WAF logs stored in a ClickHouse database. The system uses multiple AI models for different tasks:
- **Reasoning**: Claude 3.5 Sonnet for orchestration and understanding user queries
- **SQL Generation**: Claude 3 Haiku for generating ClickHouse-compatible SQL queries
- **Response Generation**: Amazon Nova Pro for creating natural language responses

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│   AWS S3    │───►│ Data Processor│───►│   ClickHouse    │
│ (WAF Logs)  │    │ (s3_to_click) │    │   Database      │
└─────────────┘    └──────────────┘    └─────────────────┘
                                                 ▲
                                                 │
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│    User     │◄──►│ Main Agent   │◄──►│  MCP Client     │
│    (CLI)    │    │ (Claude 3.5) │    │                 │
└─────────────┘    └──────────────┘    └─────────────────┘
                           │
                           ▼
                   ┌──────────────┐    ┌─────────────────┐
                   │ SQL Agent    │    │Response Agent   │
                   │(Claude Haiku)│    │(Amazon Nova Pro)│
                   └──────────────┘    └─────────────────┘
```

The system consists of several key components:

1. **Main Agent** (`main.py`) - Orchestrates the entire workflow using Strands Agents
2. **Data Processor** (`s3_to_clickhouse.py`) - Ingests WAF logs from S3 into ClickHouse
3. **MCP Integration** - Connects to ClickHouse via Model Context Protocol
4. **Utility Functions** (`utility.py`) - Logging and helper functions

### Workflow

1. **Data Ingestion**: WAF logs are processed from S3 and stored in ClickHouse
2. **User Query**: User asks natural language questions via CLI
3. **Query Processing**: Main agent (Claude 3.5 Sonnet) orchestrates the workflow
4. **SQL Generation**: Specialized agent (Claude 3 Haiku) converts query to SQL
5. **Database Query**: MCP client executes SQL against ClickHouse
6. **Response Generation**: Another agent (Amazon Nova Pro) creates natural language response
7. **User Response**: Final answer is presented to the user

## Features

- **Natural Language Queries**: Ask questions about WAF logs in plain English
- **Intelligent SQL Generation**: Automatically generates ClickHouse-compatible SQL queries
- **Multi-Model Architecture**: Uses specialized models for different tasks
- **Interactive CLI**: Real-time conversation interface
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Prerequisites

- Python 3.11+
- ClickHouse database
- AWS credentials (for S3 access)
- Bedrock access for AI models

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure MCP settings in `mcp.json`:
```json
{
    "command": "uv",
    "args": [
        "--directory",
        "<full path of clickhouse mcp server location>",
        "run",
        "mcp-clickhouse"
    ],
    "env": {
        "CLICKHOUSE_HOST": "<CLICKHOUSE_HOST>",
        "CLICKHOUSE_PORT": "<CLICKHOUSE_PORT e.g. 8123>",
        "CLICKHOUSE_SECURE": "false",
        "CLICKHOUSE_VERIFY": "false",
        "CLICKHOUSE_CONNECT_TIMEOUT": "30",
        "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": "30",
        "CLICKHOUSE_DATABASE": "default",
        "CLICKHOUSE_USER": "<Username>",
        "CLICKHOUSE_PASSWORD": "<Password>"
    }
}
```

## Setup

### 1. Data Ingestion

First, ingest your WAF logs from S3 into ClickHouse:

```python
# Update S3 bucket configuration in s3_to_clickhouse.py
WAF_LOGS_BUCKET = 'your-waf-logs-bucket'
WAF_LOGS_BUCKET_PREFIX = 'your-prefix'

# Run the data processor
python s3_to_clickhouse.py
```

This creates a `waf_logs` table with the following schema:
- `timestamp` - Log timestamp
- `action` - WAF action (ALLOW/BLOCK)
- `http_client_ip` - Client IP address
- `http_country` - Client country
- `webacl_id` - Web ACL identifier
- `terminating_rule_id` - Rule that processed the request
- And many more fields for comprehensive analysis

### 2. Run the Agent

Start the interactive agent:

```bash
python main.py
```

## Usage Examples

The system can answer various types of questions about your WAF logs:

```
> help me with the blocked ip addresses
> which acl rules blocked client ip "192.168.1.1"
> help me with blocked ips and datetime by country
> find any blocked client ips in last 7 days
> help me with blocked header host along with the rule ids
> find a list of countries with number of blocked requests in descending order on 10th May before 4pm
> which web acl were blocking requests on example.com host
> how many times client ip 192.168.1.1 was blocked on 10th May
```

## Key Components

### Tools

- **`generate_sql_statement`**: Converts natural language queries to ClickHouse SQL
- **`generate_response`**: Creates human-readable responses from query results

### Models Configuration

```python
REASONING_MODEL = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
SQL_GENERATION_MODEL = "us.anthropic.claude-3-haiku-20240307-v1:0"
RESPONSE_GENERATION_MODEL = "us.amazon.nova-pro-v1:0"
```

### Database Schema

The WAF logs table includes comprehensive fields for security analysis:
- HTTP request details (IP, country, URI, method)
- WAF decision information (action, rules)
- Request headers for detailed analysis
- Timestamps for temporal analysis

## File Structure

```
waf-logs-in-clickhouse-with-mcp/
├── main.py                 # Main agent orchestrator
├── s3_to_clickhouse.py     # Data ingestion from S3
├── utility.py              # Helper functions and logging
├── mcp.json               # MCP server configuration
├── requirements.txt       # Python dependencies
└── sample_questions.txt   # Example queries
```

## Dependencies

- `strands-agents` - Core agent framework
- `strands-agents-tools` - Additional tools
- `clickhouse-connect` - ClickHouse database connectivity
- `mcp` - Model Context Protocol support

