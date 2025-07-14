# Llama4 DeepResearch Applications

This directory contains Llama4-based DeepResearch applications built on the Strands framework. These applications demonstrate different deployment approaches for Llama4 models including AWS Bedrock, LlamaAPI, and Ollama hosting.

## Files Overview

### Bedrock Deployment

#### `llama4-DeepResearch-strands-Bedrock.py`
**Purpose**: Multi-turn deep research using Llama4 via AWS Bedrock

**Key Features**:
- **AWS Bedrock Integration**: Uses `us.meta.llama4-maverick-17b-instruct-v1:0` model
- **Multi-turn Processing**: Breaks research into discrete sequential steps
- **Guardrail Integration**: Built-in AWS Bedrock Guardrails support
- **CLI Interface**: Command-line interaction with debug mode
- **Error Handling**: Retry logic with 60-second delays
- **Stop Reason Handling**: Detects guardrail interventions

### LlamaAPI Deployment

#### `llama4-DeepResearch-strands-llamaApi.py`
**Purpose**: CLI version using LlamaAPI for model access

**Key Features**:
- **LlamaAPI Integration**: Uses `Llama-4-Maverick-17B-128E-Instruct-FP8` model
- **Environment Variables**: Secure API key management via `LLAMA_API_KEY`
- **Multi-turn Workflow**: Same research pipeline as Bedrock version
- **Callback Handler**: Real-time tool usage feedback
- **AWS Guardrails**: Optional content filtering support
- **Error Recovery**: Exception handling with retry mechanisms

#### `llama4-DeepResearch-strands-llamaApi-UI.py`
**Purpose**: Streamlit web UI version of LlamaAPI implementation

**Key Features**:
- **Web Interface**: Streamlit-based chat interface
- **Real-time Progress**: Live updates during research phases
- **Question Display**: Shows generated research questions
- **Tool Visibility**: Displays active tool usage (web search, ArXiv, etc.)
- **Session Management**: Maintains chat history
- **Guardrail Feedback**: UI-friendly guardrail notifications

### Ollama Deployment

#### `llama4-DeepResearch-strands-ollama.py`
**Purpose**: CLI version using Ollama for local/remote model hosting

**Key Features**:
- **Ollama Integration**: Uses `llama4:maverick` model
- **Self-hosted Option**: Configurable Ollama server endpoint
- **Keep-alive Settings**: 30-minute model persistence
- **Multi-turn Processing**: Standard research workflow
- **Guardrails Support**: AWS Bedrock Guardrails integration
- **Error Handling**: Robust exception handling

#### `llama4-DeepResearch-strands-ollama-UI.py`
**Purpose**: Streamlit web UI for Ollama deployment

**Key Features**:
- **Web Interface**: Streamlit chat interface
- **Remote Ollama**: Connects to remote Ollama server
- **Question Processing**: Shows research questions being processed
- **Tool Feedback**: Real-time tool usage notifications
- **Progress Tracking**: Visual progress through research phases

### Testing and Utilities

#### `llama4-api-test.py`
**Purpose**: Basic API connectivity test for LlamaAPI

**Key Features**:
- **Simple Test**: Basic chat completion test
- **API Validation**: Verifies LlamaAPI connectivity
- **Environment Setup**: Uses `LLAMA_API_KEY` environment variable
- **Model Testing**: Tests `Llama-4-Maverick-17B-128E-Instruct-FP8`

#### `llama4-strands-bedrock.py`
**Purpose**: Basic Bedrock integration test

**Key Features**:
- **Bedrock Model Test**: Tests `us.meta.llama4-scout-17b-instruct-v1:0`
- **Simple Agent**: Basic Strands agent implementation
- **Configuration Test**: Validates Bedrock model configuration

#### `llama4-strands-ui.py`
**Purpose**: Legacy Streamlit UI with hardcoded configurations

**Key Features**:
- **Streamlit Interface**: Web-based research interface
- **Hardcoded API Keys**:   Contains embedded API keys
- **Research Pipeline**: Standard multi-turn workflow
- **Guardrails Integration**: AWS Bedrock content filtering

## Configuration

### Environment Variables

```bash
# LlamaAPI versions
export LLAMA_API_KEY="your-llama-api-key"

# Ollama versions
export OLLAMA_HOST="http://your-ollama-server:11434"

# MCP Server
export MCP_SERVER="http://localhost:8000/mcp/"

# Optional AWS Guardrails
export AWS_GUARDRAIL_ID="your-guardrail-id"
export AWS_GUARDRAIL_VERSION="1"
```

### Script Configuration

All applications support these configuration variables:
- `NUM_QUESTIONS`: Number of research questions (default: 3)
- `INTERNAL_SEARCH`: Enable AWS Knowledge Base searches ("true"/"false")
- `USE_GUARDRAILS`: Enable AWS Bedrock Guardrails ("true"/"false")
- `DEBUG`: Enable verbose output (0/1)

## Model Deployment Comparison

| Deployment | Model | Hosting | Pros | Cons |
|------------|-------|---------|------|------|
| **Bedrock** | `llama4-maverick-17b-instruct-v1:0` | AWS Managed | Integrated guardrails, scalable | AWS-specific, cost |
| **LlamaAPI** | `Llama-4-Maverick-17B-128E-Instruct-FP8` | API Service | Easy setup, managed | API dependency, rate limits |
| **Ollama** | `llama4:maverick` | Self-hosted | Full control, local | Setup complexity, hardware requirements |

## Usage Examples

### Bedrock Deployment
```bash
python llama4-DeepResearch-strands-Bedrock.py
```

### LlamaAPI Deployment
```bash
# CLI version
python llama4-DeepResearch-strands-llamaApi.py

# Web UI version
streamlit run llama4-DeepResearch-strands-llamaApi-UI.py
```

### Ollama Deployment
```bash
# CLI version
python llama4-DeepResearch-strands-ollama.py

# Web UI version
streamlit run llama4-DeepResearch-strands-ollama-UI.py
```

### Testing
```bash
# Test LlamaAPI connectivity
python llama4-api-test.py

# Test Bedrock integration
python llama4-strands-bedrock.py
```

## Dependencies

```bash
# Core dependencies
pip install strands strands-agents strands-tools mcp boto3 streamlit

# LlamaAPI versions
pip install llama-api-client

# Ollama versions (requires Ollama server)
# Install Ollama separately: https://ollama.ai/
```

## Security Considerations

  **Important Security Notes**:
- `llama4-strands-ui.py` contains hardcoded API keys - avoid using in production
- Use environment variables for all API keys
- AWS Guardrails provide content filtering but require proper configuration
- Ollama deployments should use secure endpoints in production

## Architecture Features

### Multi-turn Processing
All applications use the same research workflow:
1. **Question Generation**: Creates multiple research questions
2. **Web Research**: Searches each question individually
3. **Academic Search**: ArXiv paper retrieval
4. **Financial Data**: Stock and news information
5. **Internal Search**: Optional knowledge base queries
6. **Report Generation**: Structured 1500-word reports

### Error Handling
- **Retry Logic**: 60-second backoff on failures
- **Guardrail Detection**: Handles content filtering gracefully
- **Exception Recovery**: Robust error handling across all versions

### Output Format
All applications generate structured reports with:
1. **Executive Summary**: Key findings overview
2. **Detailed Analysis**: Supporting data and insights
3. **Supporting Data**: Evidence and statistics
4. **Reference Links**: Follow-up resources

## Customization

Research behavior can be customized by:
- Adjusting model parameters (temperature, max_tokens)
- Modifying research question count
- Enabling/disabling internal searches
- Configuring guardrails for domain restrictions
- Customizing report formats and sections