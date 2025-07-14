# AI Agent Technical Reference - Weather Agent Project

> **For AI Agents Only**: This file contains technical implementation details for AI assistants.
> **Humans should refer to README.md** for complete deployment instructions and tutorials.

## 🎯 Project State Summary

**Current Status**: Production-ready three-service AI agent architecture with EKS deployment capability
**Key Achievement**: Three separate services - Web UI with OAuth auth, Agent service with triple protocols, and dedicated MCP server

## 🏗️ Technical Architecture

### Core Implementation
- **Three-Service Architecture**: Separate Helm deployments for Web UI, Agent Service, and MCP Server
- **Web UI Service**: FastAPI frontend with OAuth provider authentication (port 8000)
- **Agent Service**: Triple protocol support - MCP (8080), A2A (9000), REST API (3000)
- **MCP Server**: Dedicated weather tools server providing forecast/alert capabilities (port 8080)
- **Multi-Architecture**: AMD64/ARM64 support via docker buildx for all three services
- **Security**: EKS Pod Identity for Bedrock access, OAuth JWT validation for web access

### File Structure (AI Agent Reference)
```
weather/
├── src/                     # Source code directory
│   ├── __init__.py          # Package initialization
│   ├── agent.py             # Core weather agent logic + configuration utilities
│   ├── agent_server_mcp.py  # MCP server (port 8080)
│   ├── agent_server_a2a.py  # A2A server (port 9000)
│   ├── agent_server_fastapi.py # FastAPI server (port 3000)
│   ├── agent_interactive.py # Interactive CLI agent
│   └── main.py              # Entry points + triple server orchestrator
├── tests/                   # E2E test suite
│   ├── __init__.py          # Test package init
│   ├── test_e2e_mcp.py      # MCP protocol test client
│   ├── test_e2e_a2a.py      # A2A protocol test client
│   ├── test_e2e_fastapi.py  # FastAPI Python test client
│   └── test_e2e_fastapi_curl.sh # Workshop-friendly curl test script
├── Dockerfile               # Multi-arch container (agent)
├── helm/                    # Kubernetes deployment charts
├── mcp-servers/             # MCP tool definitions
│   └── weather-mcp-server/  # Weather MCP server
├── pyproject.toml          # Entry points configuration
├── README.md               # Human-readable deployment tutorial
└── AmazonQ.md              # This file - AI Agent technical reference
```

## 🔧 Entry Points Configuration

```python
# pyproject.toml [project.scripts]
"mcp-server"       = "src.main:main_mcp_server"    # MCP only
"a2a-server"       = "src.main:main_a2a_server"    # A2A only
"fastapi-server"   = "src.main:main_fastapi"       # FastAPI only
"interactive"      = "src.main:main_interactive"   # CLI mode
"agent"            = "src.main:servers"            # All three servers (DEFAULT)
"test-e2e-mcp"     = "tests.test_e2e_mcp:run_main"   # MCP e2e tests
"test-e2e-a2a"     = "tests.test_e2e_a2a:run_main"   # A2A e2e tests
"test-e2e-fastapi" = "tests.test_e2e_fastapi:main"   # FastAPI e2e tests
```
- **Implementation**: Markdown-based configuration in `agent.md`
- **Override**: `AGENT_CONFIG_FILE` environment variable support
- **Parsing**: Regex-based section extraction from markdown
- **Fallback**: Built-in defaults featuring "CloudBot" - a cheerful AI agent perfect for AWS workshops and demos
- **Requirement**: MD configuration file is **required** - system will raise error if no config found

### 2. Triple Server Architecture
- **Implementation**: `servers()` using subprocess-based concurrency with proper signal handling
- **Rationale**: Eliminates shutdown issues by running each server as separate subprocess
- **Entry Point**: `agent` (default Docker CMD and main.py behavior)
- **Shutdown**: Graceful termination with 2-second timeout, then force kill

### 3. Transport Protocol Change
- **Change**: `agent_server_mcp.py` default from `stdio` → `streamable-http`
- **Impact**: Eliminates need for CLI args in container deployment
- **Compatibility**: Maintains stdio support via `--transport stdio`

### 4. FastAPI Integration
- **Implementation**: FastAPI-based API in `agent_server_fastapi.py`
- **Integration**: Uses existing `weather_assistant()` function from `agent.py`
- **Endpoints**: `/health`, `/prompt`

### 5. Multi-Architecture Build Strategy
- **Issue Resolved**: `exec format error` on mixed EKS node types
- **Solution**: `docker buildx --platform linux/amd64,linux/arm64`
- **Verification**: `docker manifest inspect <image>`

## 🔧 Entry Points Configuration

```python
# pyproject.toml [project.scripts]
"mcp-server"       = "src.main:main_mcp_server"    # MCP only
"a2a-server"       = "src.main:main_a2a_server"    # A2A only
"fastapi-server"   = "src.main:main_fastapi"       # FastAPI only
"interactive"      = "src.main:main_interactive"   # CLI mode
"agent"            = "src.main:servers"            # All three servers (DEFAULT)
"test-e2e-mcp"     = "tests.test_e2e_mcp:run_main"   # MCP e2e tests
"test-e2e-a2a"     = "tests.test_e2e_a2a:run_main"   # A2A e2e tests
"test-e2e-fastapi" = "tests.test_e2e_fastapi:main"   # FastAPI e2e tests
```

## 📊 Standardized Logging Configuration

All modules in `src/` follow the same logging configuration pattern established in `main.py`:

```python
# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG') == '1' else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger(__name__)
```

**Key Features:**
- **Environment-based Level**: `DEBUG=1` enables debug logging, otherwise INFO level
- **Consistent Format**: Timestamp, module name, level, and message
- **Stdout Output**: All logs go to stdout for container compatibility
- **Force Override**: Ensures configuration takes precedence over other logging setups
- **Module-specific Loggers**: Each module gets its own logger with `__name__`

**Usage Examples:**
```bash
# Normal logging (INFO level)
uv run agent

# Debug logging (DEBUG level)
DEBUG=1 uv run agent

# Container with debug logging
docker run -e DEBUG=1 weather-agent
```

```python
# src/main.py default behavior
if __name__ == "__main__":
    servers()  # Changed from main_interactive() to servers()
```

## 🐳 Container Environment

### Required Environment Variables
```bash
MCP_PORT=8080                                                    # MCP server port
A2A_PORT=9000                                                    # A2A server port
FASTAPI_PORT=3000                                                # FastAPI server port
BEDROCK_MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0  # Bedrock model
AWS_REGION=us-west-2                                            # AWS region
```

### Build Commands (AI Reference)
```bash
# Multi-arch build and push
docker buildx build --platform linux/amd64,linux/arm64 -t ${ECR_REPO_URI}:latest --push .

# Local testing
docker build -t weather-agent .
docker run -p 8080:8080 -p 9000:9000 -p 3000:3000 -e AWS_REGION=us-west-2 weather-agent
```

## 🔍 AI Agent Troubleshooting Database

### Issue: Architecture Mismatch
- **Symptom**: `exec format error` in pod logs
- **Root Cause**: Single-arch image on incompatible node
- **Fix**: Verify multi-arch with `docker manifest inspect`
- **Prevention**: Always use `--platform linux/amd64,linux/arm64`

### Issue: Health Check Failures
- **Symptom**: Pod CrashLoopBackOff, health check timeouts
- **Root Cause**: Wrong transport or port configuration
- **Fix**: Ensure streamable-http transport and correct ports (8080/9000/3000)
- **Debug**: Check `kubectl logs deployment/weather-agent`

### Issue: Shutdown Problems
- **Symptom**: `uv run agent` doesn't respond to Ctrl+C properly
- **Root Cause**: Signal interception by uv process wrapper
- **Fix**: Use direct Python execution: `python3 main.py`
- **Alternative**: Use `uv run agent` but expect to need force kill

### Issue: Single Protocol Access
- **Symptom**: Only MCP or A2A accessible, not both
- **Root Cause**: Wrong entry point in Dockerfile
- **Fix**: Ensure `CMD ["agent"]`
- **Verification**: Test both `curl localhost:8080` and `curl localhost:9000`

### Issue: FastAPI Not Responding
- **Symptom**: FastAPI endpoints return 404 or connection refused
- **Root Cause**: FastAPI dependency missing or wrong port configuration
- **Fix**: Ensure FastAPI is installed and FASTAPI_PORT=3000
- **Verification**: Test `curl localhost:3000/health`

### Issue: Mermaid Diagram Rendering
- **Symptom**: "Unsupported markdown: list" in GitHub
- **Root Cause**: Numbered arrows or HTML tags in diagram
- **Fix**: Use plain text labels, avoid `1.`, `2.`, `<br/>` tags

## 🧪 Test Client Architecture (AI Reference)

### Test Client Design Pattern
All three test clients follow a consistent architecture:

```python
# Common pattern across all test clients
async def wait_for_server(base_url: str, timeout: int = 30):
    """Wait for server availability with timeout"""

async def test_protocol(base_url: str):
    """Main test function with numbered tests"""
    print(f"Testing Protocol at {base_url}")
    print("=" * 50)

    # Test 1: Basic connectivity
    # Test 2: Protocol handshake
    # Test 3-N: Functionality tests

    print("=" * 50)
    print("Protocol testing completed!")

def main():
    """Entry point with server checking"""
```

### MCP Test Client (`tests/test_e2e_mcp.py`)
- **Protocol**: StreamableHTTP with SSE
- **Tests**: 6 tests (0-5)
- **Key Features**: Session initialization, tool discovery, tool execution
- **Connection**: `streamablehttp_client()` with proper tuple unpacking

### A2A Test Client (`tests/test_e2e_a2a.py`)
- **Protocol**: HTTP with JSON-RPC
- **Tests**: 6 tests (1-6)
- **Key Features**: Agent card discovery, client initialization, message sending
- **Connection**: `A2ACardResolver` and `A2AClient`

### FastAPI Test Client (`tests/test_e2e_fastapi.py`)
- **Protocol**: HTTP with FastAPI
- **Tests**: 6 tests (1-6)
- **Key Features**: Async HTTP testing, health checks, weather endpoints, error handling
- **Connection**: aiohttp with async/await

### FastAPI Test Client (`tests/test_e2e_fastapi_curl.sh`)
- **Protocol**: HTTP with FastAPI
- **Tests**: 6 tests (1-6)
- **Key Features**: Health checks, weather endpoints, error handling
- **Connection**: Standard `curl` with JSON requests

### Test Output Consistency
```
Testing [Protocol] at [URL]
==================================================
1. Testing [feature]...
✅ [Feature] successful
   [Details]

2. Testing [feature]...
✅ [Feature] successful
   [Details]
==================================================
[Protocol] testing completed!
```

## 🧪 Triple Protocol Test Suite

### Professional Test Clients
All three test clients provide consistent user experience:
- **Server Readiness**: Automatic availability checking with timeouts
- **Structured Output**: Numbered tests with ✅/❌ indicators
- **Comprehensive Coverage**: Protocol-specific functionality testing
- **Error Handling**: Graceful failure handling and clear messages
- **Response Formatting**: Clean preview of responses with truncation

### MCP Test Client (`tests/test_e2e_mcp.py`)
```bash
# Tests: 6 comprehensive MCP protocol tests (0-5)
uv run test-e2e-mcp
```
**Test Coverage:**
- HTTP connectivity and SSE validation
- MCP session initialization and protocol negotiation
- Tool discovery with parameter enumeration
- Weather forecast tool execution
- Weather alert tool execution
- Complex multi-city weather comparisons

### A2A Test Client (`tests/test_e2e_a2a.py`)
```bash
# Tests: 6 comprehensive A2A protocol tests (1-6)
uv run test-e2e-a2a
```
**Test Coverage:**
- Agent card discovery and capabilities
- A2A client initialization and connection
- Weather forecast queries with formatted responses
- Weather alert queries with response validation
- Invalid message format handling
- Full response display with markdown rendering

### FastAPI Test Client (`tests/test_e2e_fastapi.py`)
```bash
# Tests: 6 comprehensive FastAPI tests (1-6)
# Requires: DISABLE_AUTH=1 uv run fastapi-server
uv run test-e2e-fastapi
```
**Test Coverage:**
- Health check endpoint validation
- Root endpoint functionality
- Weather forecast queries with async HTTP
- Alert queries with response validation
- Error handling (empty text, 404 responses)
- Async/await pattern with aiohttp

### FastAPI Test Client (`tests/test_e2e_fastapi_curl.sh`)
```bash
# Tests: 6 comprehensive FastAPI tests (1-6)
./tests/test_e2e_fastapi_curl.sh
```
**Test Coverage:**
- Health check endpoint validation
- FastAPI endpoint functionality with weather queries
- Response validation and formatting

**Note:** FastAPI tests require authentication to be disabled. Run the server with:
```bash
DISABLE_AUTH=1 uv run fastapi-server
```

### Test Suite Execution
```bash
# Start triple server
uv run agent

# Run all tests (in separate terminals)
uv run test-e2e-mcp        # Port 8080
uv run test-e2e-a2a        # Port 9000
uv run test-e2e-fastapi    # Port 3000 (requires DISABLE_AUTH=1 server)
./tests/test_e2e_fastapi_curl.sh # Port 3000 (requires DISABLE_AUTH=1 server)
```

### Development Testing
```bash
# Test triple server locally (recommended - best shutdown behavior)
python3 main.py

# Alternative (may have shutdown issues with uv signal handling)
uv run agent

# Test individual protocols
uv run mcp-server --transport stdio
uv run a2a-server
uv run fastapi-server                # For production (with auth)
DISABLE_AUTH=1 uv run fastapi-server # For testing (without auth)

# Protocol verification
uv run test-e2e-mcp               # MCP: http://localhost:8080/mcp
uv run test-e2e-a2a               # A2A: http://localhost:9000
uv run test-e2e-fastapi           # FastAPI: http://localhost:3000 (requires DISABLE_AUTH=1)
./tests/test_e2e_fastapi_curl.sh        # FastAPI: http://localhost:3000 (requires DISABLE_AUTH=1)

```

### EKS Operations
```bash
# Deployment status
kubectl get pods -l app.kubernetes.io/instance=weather-agent
kubectl logs deployment/weather-agent

# Debug commands
kubectl describe pod <pod-name>
kubectl get events --sort-by=.metadata.creationTimestamp

# Port forwarding for testing
kubectl port-forward service/weather-agent 8080:8080 9000:9000 3000:3000

# Test all protocols
uv run test-e2e-mcp        # MCP Protocol validation
uv run test-e2e-a2a        # A2A Protocol validation
uv run test-e2e-fastapi    # FastAPI validation
./tests/test_e2e_fastapi_curl.sh # FastAPI validation
```

## 🎯 AI Agent Workflow Guidelines

### Before Making Changes
1. Read both AmazonQ.md (this file) and README.md
2. Identify which documentation sections will be affected
3. Note current entry points and configuration

### During Implementation
1. Test changes locally with `agent`
2. Verify all protocols work (MCP:8080, A2A:9000, REST:3000)
3. Update entry points if pyproject.toml changes
4. Test multi-architecture builds if Dockerfile changes

### After Changes
1. Update technical details in AmazonQ.md
2. Update user instructions in README.md
3. Verify all command examples work
4. Test container build and deployment

## 🔗 Key Resources (AI Reference)

- **EKS Cluster**: `agents-on-eks` (us-west-2)
- **ECR Repository**: `agents-on-eks/weather-agent`
- **Bedrock Model**: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`
- **MCP Inspector**: `npx @modelcontextprotocol/inspector`
- **A2A Test Client**: `uv run test-e2e-a2a`
- **FastAPI Test Client**: `./tests/test_e2e_fastapi_curl.sh`

---

## 🤖 AI Agent Documentation Maintenance Protocol

### CRITICAL: Dual Documentation Strategy

**AmazonQ.md (This File)**:
- Technical implementation details
- Troubleshooting database
- Quick command reference
- Architecture decisions
- AI Agent workflow guidance

**README.md**:
- Complete human-readable tutorial
- Step-by-step deployment instructions
- Prerequisites and explanations
- Architecture diagrams
- User-facing documentation

### Synchronization Requirements

When making changes, AI Agents MUST update both files:

#### AmazonQ.md Updates:
- [ ] Entry points table if pyproject.toml changes
- [ ] Docker CMD if Dockerfile changes
- [ ] Quick commands with new entry points
- [ ] Technical decisions for architectural changes
- [ ] Troubleshooting database for new issues
- [ ] File structure if files added/renamed

#### README.md Updates:
- [ ] Command examples with new entry points
- [ ] Environment variables if added/changed
- [ ] Deployment steps if process changes
- [ ] Prerequisites if tools/versions change
- [ ] Architecture diagram if structure changes
- [ ] Troubleshooting table for user-facing issues

### Critical Consistency Points
These MUST be identical across both files:
- Entry point names (`mcp-server`, `a2a-server`, etc.)
- Port numbers (8080 for MCP, 9000 for A2A, 3000 for REST API)
- Environment variables (BEDROCK_MODEL_ID, AWS_REGION, etc.)
- Resource names (cluster, IAM roles, ECR repositories)

### Common AI Agent Mistakes to Avoid
1. **Updating only one file** - Always update both
2. **Inconsistent commands** - Test all examples
3. **Outdated entry points** - Check pyproject.toml references
4. **Missing environment variables** - Document all required vars
5. **Broken container builds** - Verify multi-arch support

---

**AI Agent Status**: This project is production-ready with comprehensive triple-protocol support and EKS deployment capability. All technical implementation details are documented above for AI Agent reference.
