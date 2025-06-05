# Development Guide

## Introduction

This guide provides comprehensive setup instructions for developers who want to leverage and extend this asset for their own use cases. The project follows a modular architecture that separates agent logic from infrastructure concerns, allowing for flexible development and deployment.

This guidance would address: 
- **Loosely Coupled Architecture**: Clear separation between agent business logic and infrastructure hosting
- **Modular Design**: Each agent operates as an independent service with well-defined interfaces
- **Local Development Support**: Full development environment that mirrors production setup
- Modify agent behavior without touching infrastructure code
- Test changes locally before deployment
- Add new agents without restructuring the existing system
- Deploy to different environments with minimal configuration changes

## Table of Content
- [Installation](#installation)
- [Local Setup Pre-requisite](#local-setup-pre-requisite)
- [Running the Servers](#running-the-servers)
- [Testing Agents](#testing-agents)
- [Using MCP Tools](#using-mcp-tools)

## Installation

- Clone the repository: 
```bash
git clone https://github.com/aws-samples/3P-Agentic-Frameworks.git
```

- Navigate to the project root directory (`a2a-advisory-trading/`): 
```
cd a2a-protocols/a2a-advisory-trading
```

## Local Setup Pre-requisite

* [Python >= 3.10](https://www.python.org/downloads/)
* [PIP >= 25.0.1](https://pypi.org/project/pip/)
* On the Console, make sure Amazon BedRock has enabled access to your model of choice
* Install uvicorn
```python
pip install uvicorn
```
* Install the requirements.txt for agents' dependencies:
```python
pip install -r iac/a2a_core/requirements.txt
```
* Install the following libraries for the CLI start:
```python
pip install pyfiglet colorama halo aiohttp boto3
```
* (Optional) Create and activate a virtual environment:
```
# For macOS/Linux
python -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate
```

* Create the `.env` in the project root directory (`a2a-advisory-trading/`) file with the following information:
```
  APP_NAME=adt
  ENV_NAME=dev
  AWS_REGION=us-east-1
  BEDROCK_MODEL_IS=your-bedrock-model-id
  AWS_ACCESS_KEY_ID=your-access-key-id
  AWS_SECRET_ACCESS_KEY=your-secret-access-key
  TRADE_LOG_TABLE=your-dynamodb-table-for-trade-logging
```

#### Environment Variables Explanation

| Variable              | Description                            | Example                      |
|-----------------------|----------------------------------------|------------------------------| 
| APP_NAME              | Application identifier                 | `adt`                        |
| ENV_NAME              | Environment name                       | `dev`, `staging`, `prod`     |
| AWS_REGION            | AWS region for services                | `us-east-1`                  |
| BEDROCK_MODEL_IS      | Your Amazon Bedrock model ID	          | `anthropic.claude-v2`        |
| AWS_ACCESS_KEY_ID     | 	AWS access key                        | From AWS IAM                 |
| AWS_SECRET_ACCESS_KEY | 	AWS secret key                        | From AWS IAM                 |
| TRADE_LOG_TABLE       | 	DynamoDB table name for trade logging | `adt-dev-trade-execution`    |

#### DynamoDB Table Configuration

**Note**: The `TRADE_LOG_TABLE` setting requires special attention:

- If you've deployed using Terraform, use the auto-generated table name
- Default format: {app_name}-{env_name}-trade-execution
- Example: adt-dev-trade-execution

If you have not deployed the solution end-to-end using Terraform module, you have 2 options:
- Create a table manually through AWS Console
- Use our provided Python script to create the table automatically

To use our Python script to create the DynamoDB table: 

```
cd local_servers
python init_dynamodb.py
```

Important Notes: 
- Ensure your DynamoDB table is in the same region as other AWS services
- Verify your AWS credentials have appropriate permissions for DynamoDB operations

## Running the Servers

#### Option 1: Run all agents servers 

From the project root directory:

```python
python dev/local_servers/servers.py
```

This will start all services on their respective ports in the same terminal:

- Market Analysis: http://localhost:8000
- Risk Assessment: http://localhost:8001
- Trade Execution: http://localhost:8002
- Portfolio Manger: http://localhost:8003

#### Option 2: Run individual server (recommended)

This option is recommended for development since developers can trace each agent operations easier with separated terminal per agent.

From the project root directory, navigate to `local_servers/`
```
cd dev/local_servers
```

Run the following commands respectively to start your agent servers:
```python
# Market Analysis Agent
uvicorn local_server_ma:app --reload --port 8000

# Risk Assessment Agent
uvicorn local_server_ra:app --reload --port 8001

# Trade Execution Agent
uvicorn local_server_te:app --reload --port 8002

# Portfolio Manager Agent
uvicorn local_server_pm:app --reload --port 8003
```

## Testing agents

Once the servers are up and running, we can test each individual agent server either using the interactive custom cli or curl command.

#### Testing with curl commands 

During agent development, using CURL commands provides a direct and efficient way to test individual agent endpoints without relying on the Portfolio Manager's routing logic. This approach is particularly useful when:

- Developing new agent functionality
- Testing agent endpoints in isolation
- Debugging specific agent responses
- Validating API endpoints before integration
- Working on agents that aren't yet connected to the Portfolio Manager

Below are the examples of the attributes we need to make the request to the server.

- For market analysis agent: 

```
curl -X POST "http://localhost:8000/task" \
  -H "Content-Type: application/json" \
  -d '{
        "task": {
          "id": "market-test-001",
          "input": {
            "sector": "clean energy",
            "focus": "investment risks",
            "riskFactors": ["regulation", "supply chain disruption"],
            "summaryLength": 100
          }
        }
      }'
```

- For risk assessment agent: 
```
curl -X POST  "http://localhost:8001/task" \
  -H "Content-Type: application/json" \
  -d '{
        "task": {
           "id": "risk-task-001",
           "input": {
        "analysisType": "asset",
        "timeHorizon": "6 months",
        "capitalExposure": "100000",
        "specificAsset": {
            "symbol": "AAPL",
            "quantity": "100",
            "action": "buy"
        }
          }
        }
      }'
```

- For trade execution agent: 
```
curl -X POST "http://localhost:8002/task" \
  -H "Content-Type: application/json" \
  -d '{
        "task": {
          "id": "trade-debug-001",
          "input": {
            "action": "Buy",
            "symbol": "AMZN",
            "quantity": 10
          }
        }
      }'
```

- For portfolio manager agent:
```
curl -X POST "http://localhost:8003/task" \
  -H "Content-Type: application/json" \
  -d '{
        "task": {
          "id": "cli-test-003",
          "input": {
            "user_input": "What is the current market and risk situation of the healthcare industry for investment?"
          }
        }
      }'
```


#### Sample of successful curl command results 

- For market analysis agent: 
```json
{
    "id": "market-test-001",
    "input": {
        "sector": "clean energy",
        "focus": "investment risks",
        "riskFactors": [
            "regulation",
            "supply chain disruption"
        ],
        "summaryLength": 100
    },
    "output": {
        "summary": "The clean energy market presents both opportunities and risks for investors. Key trends include growing global demand for renewable sources, technological advancements, and supportive government policies. However, the sector faces regulatory uncertainties, supply chain disruptions, and competition from traditional energy sources. Investors must carefully consider the risks, such as changes in renewable energy subsidies, raw material shortages, and the impact of geopolitical tensions on global trade. Despite these challenges, the long-term outlook for clean energy remains positive, driven by the urgent need to address climate change and the increasing cost-competitiveness of renewable technologies. Diversification and thorough risk assessment are crucial for investors navigating this dynamic and evolving market.",
        "tags": [
            "clean energy",
            "renewable energy",
            "technological advancements",
            "government policies",
            "regulatory uncertainties",
            "supply chain disruptions",
            "competition from traditional energy"
        ],
        "sentiment": "positive"
    },
    "status": "completed",
    "messages": [],
    "error": null,
    "created_at": "2025-05-31T17:52:53.320431",
    "modified_at": "2025-05-31T17:52:56.235887",
    "requires_input": false,
    "metadata": {}
}
```

- For risk assessment agent: 

```json
{
    "id": "risk-task-001",
    "input": {
        "action": "Buy",
        "symbol": "TSLA",
        "quantity": 25,
        "sector": "electric vehicles",
        "priceVolatility": "high",
        "timeHorizon": "short-term",
        "marketConditions": "uncertain",
        "capitalExposure": "moderate"
    },
    "output": {
        "score": 75,
        "rating": "Moderate",
        "factors": [
            "rising_interest_rates",
            "geopolitical_tensions",
            "inflationary_pressures"
        ],
        "explanation": "The current market environment presents moderate risk for short-term investments with moderate capital exposure. Factors such as rising interest rates, geopolitical tensions, and persistent inflationary pressures are contributing to increased market volatility and economic uncertainty. While the overall market outlook remains cautious, diversification and close monitoring of macroeconomic indicators can help mitigate the potential impact of these risks."
    },
    "status": "completed",
    "messages": [],
    "error": null,
    "created_at": "2025-05-31T19:01:18.148797",
    "modified_at": "2025-05-31T19:01:19.913096",
    "requires_input": false,
    "metadata": {}
}
```

- For trade execution agent: 
```json
{
    "id": "trade-debug-001",
    "input": {
        "action": "Buy",
        "symbol": "AMZN",
        "quantity": 10
    },
    "output": {
        "status": "executed",
        "confirmationId": "TRADE-1CE93C2E"
    },
    "status": "completed",
    "messages": [],
    "error": null,
    "created_at": "2025-05-31T18:56:26.022748",
    "modified_at": "2025-05-31T18:56:26.506165",
    "requires_input": false,
    "metadata": {}
}
```

- For portfolio manager agent: 
```json
{
    "id": "cli-test-003",
    "input": {
        "user_input": "What is the current market and risk situation of the healthcare industry for investment?"
    },
    "output": {
        "status": "pending",
        "analysis_results": {
            "MarketSummary": {
                "status": "completed",
                "response": {
                    "summary": "The healthcare sector has faced a complex market environment in recent times. The COVID-19 pandemic has significantly impacted the industry, leading to increased demand for healthcare services and products, but also supply chain disruptions and financial pressures.\n\nKey trends include the growing emphasis on telehealth and digital healthcare solutions, the rise of personalized medicine, and the continued focus on cost-effective and value-based care. Opportunities lie in the development of innovative treatments, the expansion of healthcare access, and the integration of technology to enhance patient outcomes.\n\nHowever, the sector also faces several risks, including regulatory changes (T), potential reimbursement challenges (B), and the ongoing threat of disease outbreaks and pandemics (D). Navigating these uncertainties requires healthcare companies to be agile, adaptable, and focused on building resilience within their operations and supply chains.",
                    "tags": [
                        "healthcare",
                        "telehealth",
                        "personalized medicine",
                        "value-based care"
                    ],
                    "sentiment": "neutral"
                }
            },
            "RiskEvaluation": {
                "status": "completed",
                "response": {
                    "score": 75,
                    "rating": "Moderate",
                    "factors": [
                        "sector_volatility",
                        "regulatory_risks",
                        "economic_uncertainty"
                    ],
                    "explanation": "The healthcare sector faces a moderate level of risk due to several factors. Sector volatility is a concern, as the industry is sensitive to changes in government policies, technological advancements, and consumer preferences. The regulatory environment also poses risks, with ongoing debates around healthcare reform and potential changes to reimbursement models. Additionally, the overall economic uncertainty stemming from factors like inflation, interest rate fluctuations, and geopolitical tensions can impact the sector's performance. While the healthcare industry is generally considered defensive, these factors warrant a moderate risk assessment for the given time horizon and capital exposure."
                }
            }
        },
        "trade_details": {},
        "session_id": "cli-test-003",
        "summary": "✅ MarketSummary completed | ✅ RiskEvaluation completed",
        "delegated_tasks": [
            "MarketSummary",
            "RiskEvaluation"
        ]
    },
    "status": "completed",
    "messages": [],
    "error": null,
    "created_at": "2025-05-31T19:05:49.373718",
    "modified_at": "2025-05-31T19:05:55.534811",
    "requires_input": false,
    "metadata": {}
}
```

## Using MCP Tools

To use the MCP tools suggested in the solution (Python Repl and http_request): 

### For Python Repl 
- Set `BYPASS_TOOL_CONSENT = true` in local environment to enable automatic approval
- Uncomment implemented code in the start of phase 2 - execute trade 

### For http_request 
- Pre-requisite: Make sure you have defined and listed all necessary access to provided resources in local environment 
- Note: Expect delay in your agents response. As the number of resources grow, this could create throttle in agents orchestration flow