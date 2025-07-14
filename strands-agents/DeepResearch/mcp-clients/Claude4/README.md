# Claude4 DeepResearch Applications

This directory contains Claude4-based DeepResearch applications built on the Strands framework. These applications demonstrate different approaches to conducting comprehensive research using AI agents.

## Files Overview

### `claude4-DeepResearch-strands-api-interleavedThinking.py`
**Purpose**: Single-turn deep research with interleaved thinking demonstration

**Key Features**:
- **Interleaved Thinking**: Enables Claude4's thinking process between tool calls using `anthropic-beta: interleaved-thinking-2025-05-14`
- **Single-turn Processing**: Completes entire research workflow in one agent call
- **AWS Guardrails**: Optional content filtering and safety controls
- **Research Pipeline**: 
  1. Generates configurable number of research questions
  2. Performs web searches via Tavily
  3. Conducts ArXiv academic paper searches
  4. Retrieves stock/financial data for companies
  5. Produces structured 1500-word reports
- **Output Format**: Executive Summary, Details, Follow-up links
- **CLI Interface**: Command-line input/output

### `claude4-DeepResearch-strands-api-IT-UI.py`
**Purpose**: Streamlit web UI version of the interleaved thinking research agent

**Key Features**:
- **Web Interface**: Streamlit-based chat interface for user interaction
- **Real-time Feedback**: Live updates during research process
- **Tool Visibility**: Shows which tools are being used (web search, ArXiv, stock info)
- **Same Research Pipeline**: Identical functionality to CLI version
- **Session Management**: Maintains chat history in Streamlit session state

### `claude4-DeepResearch-strands-api-workflow.py`
**Purpose**: Multi-turn workflow-based research system

**Key Features**:
- **Multi-turn Processing**: Breaks research into discrete, sequential steps
- **Step-by-step Execution**: Each research phase is a separate agent call
- **Modular Design**: Functions for guardrail checks and workflow turns
- **Error Handling**: Retry logic with 60-second backoff delays
- **Custom Report Planning**: Generates research plan before execution
- **CLI Interface**: Command-line interaction

**Workflow Steps**:
1. Question generation from user prompt
2. Individual web searches per generated question
3. ArXiv academic search
4. Stock information retrieval (if company mentioned)
5. Company news gathering (if applicable)
6. Internal data source search (optional)
7. Report planning and generation

### `claude4-DeepResearch-strands-api-workflowUI.py`
**Purpose**: Streamlit UI version of the multi-turn workflow system

**Key Features**:
- **Web Interface**: Streamlit implementation of workflow approach
- **Visual Progress**: Shows each research question being processed
- **Step Visualization**: Displays current research phase
- **Error Handling**: UI-friendly error messages and recovery
- **Question Display**: Shows generated research questions with guardrail filtering

## Configuration Options

All applications support these environment variables:

```bash
# Required
export ANTHROPIC_API_KEY="your-api-key"
export MCP_SERVER="http://localhost:8000/mcp/"

# Optional AWS Guardrails
export AWS_GUARDRAIL_ID="your-guardrail-id"
export AWS_GUARDRAIL_VERSION="1"
```

**Script Configuration Variables**:
- `NUM_QUESTIONS`: Number of research questions to generate (default: 3)
- `INTERNAL_SEARCH`: Enable AWS Knowledge Base searches ("true"/"false")
- `USE_GUARDRAILS`: Enable AWS Bedrock Guardrails ("true"/"false")
- `DEBUG`: Enable verbose output (0/1)

## Usage Examples

### Command Line Interfaces
```bash
# Interleaved thinking approach
python claude4-DeepResearch-strands-api-interleavedThinking.py

# Multi-turn workflow approach
python claude4-DeepResearch-strands-api-workflow.py
```

### Web UI Interfaces
```bash
# Interleaved thinking UI
streamlit run claude4-DeepResearch-strands-api-IT-UI.py

# Multi-turn workflow UI
streamlit run claude4-DeepResearch-strands-api-workflowUI.py
```

## Dependencies

```bash
pip install strands strands-agents strands-agents-tools anthropic mcp boto3 streamlit
```

## Architecture Comparison

| Feature | Interleaved Thinking | Multi-turn Workflow |
|---------|---------------------|-------------------|
| **Processing** | Single agent call | Multiple sequential calls |
| **Thinking** | Visible between tool calls | Standard processing |
| **Control** | Less granular | Step-by-step control |
| **Error Handling** | Built-in retry | Custom retry per step |
| **Debugging** | Thinking process visible | Detailed step logging |
| **Performance** | Faster execution | More controllable |

## Security Features

- **AWS Guardrails**: Content filtering for inputs and outputs
- **Environment Variables**: Secure API key management
- **Error Handling**: Graceful failure with retry mechanisms
- **Input Validation**: Guardrail checks on user prompts

## Output Format

All applications generate structured reports with:
1. **Executive Summary**: Key findings in paragraph form
2. **Detailed Analysis**: Supporting data and insights
3. **Reference Links**: Follow-up resources for further research

## Customization

Research behavior can be customized by:
- Adjusting `NUM_QUESTIONS` for research depth
- Modifying system prompts for different report formats
- Enabling/disabling internal searches
- Configuring guardrails for domain-specific restrictions
- Customizing callback handlers for different output formats