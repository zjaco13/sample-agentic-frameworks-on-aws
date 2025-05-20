# Financial Analysis Agent

> An intelligent financial assistant powered by LangGraph and AWS Bedrock with MCP integration

<div align="left"><img src="./public/stock_prices.png" width="800" alt="Stock Prices" /></div>

<div align="left"><img src="./public/financial_search.png" width="800" alt="Financial Search" /></div>

<div align="left"><img src="./public/visualization.png" width="800" alt="Visualization" /></div>


## Overview

The Financial Analysis Agent is an AI-powered assistant designed to handle a wide range of financial requirements and queries. Built on a hybrid architecture that combines LangGraph's structured reasoning with AWS Bedrock's powerful language models, this agent can analyze financial data, provide insights, and assist with financial decision-making.

## Key Features

- **Financial Domain Expertise**: Capable of processing and analyzing financial requirements, stock data, market trends, and other financial information
- **LangGraph + AWS Bedrock Integration**: Combines the structured reasoning workflow of LangGraph with the powerful language models from AWS Bedrock
- **Modular MCP (Model Context Protocol) Integration**: Expandable functionality through standardized MCP tools for various financial domains
- **Interactive User Interface**: Clean, intuitive interface for natural conversation about financial topics
- **Transparent Reasoning**: Visible thought process panel showing how the agent reasons through financial questions

## Architecture

The system architecture combines several key technologies:

### Why LangGraph?

LangGraph provides several advantages for this agent:

- **Modular Development**: Break down complex financial reasoning into manageable components
- **Intuitive Reasoning Flow**: Program the agent's thought process at the architectural level 
- **Structured Control Flow**: Direct how the agent approaches different financial questions
- **Recursive Processing**: Allow agents to recursively process financial information until reaching a satisfactory answer

### Agent Workflow

The agent employs a ReAct (Reasoning + Action) approach to solve financial queries:

1. Agent receives a financial question from the user
2. Using LangGraph, it structures its reasoning about how to approach the problem
3. It determines what tools might be needed to answer the query
4. It dynamically accesses the necessary MCP tools using a standardized protocol
5. It processes the information recursively, going back to reasoning when needed
6. It presents a comprehensive answer to the user

### MCP Tool Integration

The agent can be extended with various MCP tools for different financial domains:

- **Financial Analysis Tools**: Ratio analysis, trend evaluation, financial statement analysis
- **Stock Market Tools**: Real-time quotes, historical data, technical indicators
- **News Analysis**: Financial news sentiment, market impact predictions
- **Portfolio Management**: Asset allocation, risk assessment, diversification analysis

To add a new MCP server:

1. Click on the settings icon in the UI
2. Enter server name and hostname in the MCP Server Settings dialog
3. Click "Add and Test Server" to validate the connection


<div align="left"><img src="./public/mcp_settings.png" width="600" alt="MCP Settings" /></div>



## Installation

### Prerequisites

- Node.js (version 18+)
- Python 3.10+
- AWS account with Bedrock access

### Setup

1. Clone the repository:

```bash
git clone https://github.com/3P-Agentic-Frameworks.git
cd 3P-Agentic-Frameworks/langgraph/financial-agent
```

2. Set up Python virtual environment:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

3. Install frontend dependencies:

```bash
npm install
```

4. Install backend dependencies:

```bash
cd py-backend
pip install -r requirements.txt
```

5. Configure environment variables:

Create a `.env.local` file in the root directory with the following variables:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region
```

## Usage

1. Start the development server:

```bash
npm run dev
```

This command will start both the Next.js frontend and the Python backend servers.

2. Open your browser to `http://localhost:3000`

3. Use the chat interface to ask financial questions

4. Configure MCP servers via the settings panel to extend functionality

<div align="left"><img src="./public/thought_process.svg" width="800" alt="Thought Process" /></div>


## Project Structure

```
financial-agent/
├── app/                # Next.js app directory
├── components/         # React components
├── hooks/             # Custom React hooks
├── lib/               # Utility functions
├── public/            # Static assets
├── py-backend/        # Python backend with FastAPI
│   ├── app/           # Backend application code
│   └── requirements.txt  # Python dependencies
├── utils/             # Frontend utilities
└── README.md          # Project documentation
```

