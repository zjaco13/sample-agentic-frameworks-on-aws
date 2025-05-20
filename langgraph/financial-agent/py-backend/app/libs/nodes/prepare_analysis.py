import logging
import asyncio
from typing import List
from contextlib import AsyncExitStack
from app.libs.types import GraphState
from app.libs.decorators import with_thought_callback, log_thought
from app.api_routes.mcp_servers import load_server_config

logger = logging.getLogger(__name__)

def get_mcp_servers() -> List[str]:
    server_configs = load_server_config()
    active_servers = [s["hostname"] for s in server_configs if s["isActive"]]
    
    if not active_servers:
        logger.warning("No active MCP servers found, falling back to default values")
        return [
            "http://localhost:8083/sse",  # stock_market_server
            "http://localhost:8084/sse",  # financial_analysis_server
            "http://localhost:8085/sse"   # web_news_server
        ]
    
    return active_servers

@with_thought_callback(category="setup", node_name="Preparation")
async def prepare_analysis(state: GraphState) -> GraphState:
    logger.info("Preparing analysis context...")
    
    new_state = state.copy()
    session_id = new_state.get("session_id")
    server_urls = get_mcp_servers()
    
    new_state["server_urls"] = server_urls
    new_state["action_groups"] = []
    new_state["tool_server_mapping"] = {}

    if "metadata" not in new_state:
        new_state["metadata"] = {}
    new_state["metadata"]["last_active_node"] = "prepare_analysis"

    log_thought(
        session_id=session_id,
        type="thought",
        category="setup",
        node="Preparation",
        content="Connecting to selected MCP servers",
        technical_details={"servers": server_urls}
    )
    await asyncio.sleep(0.5)

    try:
        async with AsyncExitStack() as exit_stack:
            all_action_groups = []
            tool_server_mapping = {}
            
            for server_url in server_urls:
                try:
                    from mcp import ClientSession
                    from mcp.client.sse import sse_client
                    
                    streams_context = await exit_stack.enter_async_context(sse_client(url=server_url))
                    read_stream, write_stream = streams_context
                    
                    session = ClientSession(read_stream, write_stream)
                    session = await exit_stack.enter_async_context(session)
                    await session.initialize()
                    
                    tools_result = await session.list_tools()
                    
                    server_parts = server_url.split('/')
                    server_name = server_parts[2].replace(':', '_') if len(server_parts) >= 3 else "mcp-server"
                    
                    if not tools_result.tools:
                        logger.warning(f"No tools available from server {server_url}")
                        continue
                    
                    action_group = {
                        'actionGroupName': f"{server_name}_tools",
                        'description': f"Financial analysis tools from {server_name} server",
                        'functionSchema': {
                            'functions': []
                        },
                        'actionGroupExecutor': {
                            'customControl': 'RETURN_CONTROL'
                        }
                    }
                    
                    for tool in tools_result.tools:
                        function = {
                            'name': tool.name,
                            'description': tool.description,
                            'parameters': {}
                        }
                        
                        if 'properties' in tool.inputSchema:
                            for param_name, param_info in tool.inputSchema['properties'].items():
                                param_type = param_info.get('type', 'string')
                                
                                if param_type == 'integer':
                                    bedrock_type = 'integer'
                                elif param_type == 'number':
                                    bedrock_type = 'number'
                                elif param_type == 'boolean':
                                    bedrock_type = 'boolean'
                                elif param_type == 'array':
                                    bedrock_type = 'array'
                                else:
                                    bedrock_type = 'string'
                                
                                function['parameters'][param_name] = {
                                    'type': bedrock_type,
                                    'description': param_info.get('description', param_info.get('title', param_name)),
                                    'required': param_name in tool.inputSchema.get('required', [])
                                }
                        
                        action_group['functionSchema']['functions'].append(function)
                        tool_server_mapping[tool.name] = server_url
                    
                    all_action_groups.append(action_group)
                    logger.info(f"Added action group from {server_url} with {len(action_group['functionSchema']['functions'])} functions")
                        
                except Exception as e:
                    logger.error(f"Error connecting to MCP server {server_url}: {str(e)}")
                    log_thought(
                        session_id=session_id,
                        type="thought",
                        category="error",
                        node="Preparation",
                        content=f"Error connecting to MCP server: {server_url}",
                        technical_details={"error": str(e)}
                    )
            
            new_state["action_groups"] = all_action_groups
            new_state["tool_server_mapping"] = tool_server_mapping
            
            log_thought(
                session_id=session_id,
                type="thought",
                category="setup",
                node="Preparation",
                content=f"Setup complete with {len(all_action_groups)} action groups and {sum(len(ag['functionSchema']['functions']) for ag in all_action_groups)} tools"
            )
            
    except Exception as e:
        logger.error(f"Error in prepare_analysis: {str(e)}")
        log_thought(
            session_id=session_id,
            type="thought",
            category="error",
            node="Preparation",
            content=f"Error preparing analysis: {str(e)}"
        )
    
    logger.info(f"Prepare analysis returning state with keys: {list(new_state.keys())}")
    logger.info(f"State includes {len(new_state.get('action_groups', []))} action groups")
    
    return new_state
