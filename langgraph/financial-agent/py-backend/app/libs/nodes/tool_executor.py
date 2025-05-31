import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from app.libs.types import GraphState
from app.libs.decorators import with_thought_callback, log_thought
from contextlib import AsyncExitStack

logger = logging.getLogger(__name__)

@with_thought_callback(category="tool", node_name="Tool Executor")
async def tool_executor(state: GraphState) -> GraphState:
    logger.info("Tool executor: Processing tool request...")
    
    new_state = state.copy()
    session_id = new_state.get("session_id")
    
    if "thought_history" not in new_state:
        new_state["thought_history"] = []
    
    if "metadata" not in new_state:
        new_state["metadata"] = {}
    
    tool_execution = new_state.get("tool_execution", {})
    function_name = tool_execution.get("function", "")
    action_group = tool_execution.get("action_group", "")
    parameters = tool_execution.get("parameters", {})
    server_url = tool_execution.get("server_url", "")
    
    if not function_name or not server_url:
        error_msg = "Missing required tool execution details (function name or server URL)"
        logger.error(error_msg)
        
        log_thought(
            session_id=session_id,
            type="thought",
            category="error",
            node="Tool Executor",
            content=f"Tool execution error: {error_msg}"
        )
        
        thought_record = {
            "type": "thought",
            "category": "error",
            "node": "Tool Executor",
            "content": f"Tool execution error: {error_msg}"
        }
        new_state["thought_history"].append(thought_record)
        
        new_state["tool_error"] = error_msg
        new_state["next"] = "perform_reasoning"
        return new_state
    
    log_thought(
        session_id=session_id,
        type="thought",
        category="tool",
        node="Tool Executor",
        content=f"Executing tool: {function_name}",
        technical_details={"parameters": parameters}
    )
    
    thought_record = {
        "type": "thought",
        "category": "tool",
        "node": "Tool Executor",
        "content": f"Executing tool: {function_name}",
        "technical_details": {"parameters": parameters}
    }
    new_state["thought_history"].append(thought_record)
    
    try:
        result = await execute_mcp_tool(server_url, function_name, parameters)
        
        result_preview = str(result)
        log_thought(
            session_id=session_id,
            type="thought",
            category="tool",
            node="Tool Executor",
            content=f"Received result from {function_name}",
            technical_details={"tool_result": result_preview}
        )
        
        thought_record = {
            "type": "thought",
            "category": "tool",
            "node": "Tool Executor",
            "content": f"Received result from {function_name}",
            "technical_details": {"tool_result": result_preview}
        }
        new_state["thought_history"].append(thought_record)
        
        new_state["tool_result"] = {
            "action_group": action_group,
            "function": function_name,
            "result": result
        }
        
        if "tool_execution" in new_state:
            del new_state["tool_execution"]
            
        new_state["next"] = "perform_reasoning"
        
    except Exception as e:
        error_msg = f"Error executing tool {function_name}: {str(e)}"
        logger.error(error_msg)
        
        log_thought(
            session_id=session_id,
            type="thought",
            category="error",
            node="Tool Executor",
            content=f"Error executing tool {function_name}",
            technical_details={"error": error_msg}
        )
        
        thought_record = {
            "type": "thought",
            "category": "error",
            "node": "Tool Executor",
            "content": f"Error executing tool {function_name}",
            "technical_details": {"error": error_msg}
        }
        new_state["thought_history"].append(thought_record)
            
        new_state["tool_error"] = error_msg
        new_state["next"] = "perform_reasoning"
    
    return new_state

async def execute_mcp_tool(server_url: str, function_name: str, parameters: Dict[str, Any]) -> Any:
    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
        
        logger.info(f"Connecting to MCP server: {server_url} for tool: {function_name}")
        
        async with AsyncExitStack() as exit_stack:
            streams_context = await exit_stack.enter_async_context(sse_client(url=server_url))
            read_stream, write_stream = streams_context
            
            session = ClientSession(read_stream, write_stream)
            session = await exit_stack.enter_async_context(session)
            await session.initialize()
            
            converted_params = convert_parameters(parameters)
            
            logger.info(f"Executing tool: {function_name} with params: {converted_params}")
            result = await session.call_tool(function_name, converted_params)
            
            if result.content and hasattr(result.content[0], 'text'):
                return result.content[0].text
            elif result.content:
                return str(result.content)
            else:
                return "Tool executed successfully but returned no content"
            
    except Exception as e:
        logger.error(f"Error in execute_mcp_tool: {e}")
        raise

def convert_parameters(parameters: Any) -> Dict[str, Any]:
    converted_params = {}
    
    if isinstance(parameters, list):
        for param in parameters:
            if isinstance(param, dict) and "name" in param and "value" in param:
                name = param["name"]
                value = param["value"]
                param_type = param.get("type")
                
                if param_type == "integer":
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        pass
                elif param_type == "number":
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        pass
                elif param_type == "boolean":
                    if isinstance(value, str):
                        value = value.lower() == "true"
                        
                converted_params[name] = value
    elif isinstance(parameters, dict):
        converted_params = parameters
    
    return converted_params