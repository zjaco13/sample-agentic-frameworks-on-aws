import logging
from typing import Dict, List
from app.libs.types import GraphState
from app.libs.financial_analyzer import FinancialAnalyzer
from app.libs.decorators import with_thought_callback, log_thought

logger = logging.getLogger(__name__)

@with_thought_callback(category="analysis", node_name="Reasoning")
async def perform_reasoning(state: GraphState) -> GraphState:
    """LangGraph node to perform reasoning with Bedrock inline agent"""
    logger.info("Performing reasoning...")

    new_state = state.copy()
    query = new_state.get("extracted_text", "")
    action_groups = new_state.get("action_groups", [])
    instruction = new_state.get("instruction", "")
    model = new_state.get("model")
    tool_server_mapping = new_state.get("tool_server_mapping", {})
    thought_history = new_state.get("thought_history", [])
    bedrock_session_id = new_state.get("bedrock_session_id")
    session_id = new_state.get("session_id")

    if bedrock_session_id:
        logger.info(f"Using Bedrock session ID: {bedrock_session_id}")

    # Check if we're continuing from tool execution
    tool_result = new_state.get("tool_result")
    invocation_id = new_state.get("invocation_id")
    tool_error = new_state.get("tool_error")
    continuing_from_tool = bool(tool_result)
    
    if "metadata" not in new_state:
        new_state["metadata"] = {}
    
    # Get or create financial analyzer
    analyzer = new_state.get("analyzer")
    if not analyzer:
        analyzer = FinancialAnalyzer(model_id=model) if model else FinancialAnalyzer()
        
        if session_id:
            analyzer.app_session_id = session_id
            
        if bedrock_session_id:
            analyzer.session_id = bedrock_session_id
            
        new_state["analyzer"] = analyzer
        
    try:
        if continuing_from_tool:
            processor_state = new_state.copy()
            processor_state["instruction"] = instruction

            analyzer_result = await analyzer.process_tool_result(processor_state)
            for key, value in analyzer_result.items():
                if key not in ["metadata", "thought_history"]:  
                    new_state[key] = value
        else:
            processor_state = new_state.copy()
            processor_state["query"] = query
            processor_state["action_groups"] = action_groups
            processor_state["instruction"] = instruction
            
            logger.debug(f"Action groups in state: {len(action_groups)} groups with {sum(len(ag['functionSchema']['functions']) for ag in action_groups)} functions")
            logger.debug(f"Tool server mapping: {tool_server_mapping}")
            
            if not action_groups:
                logger.error("Action groups missing or empty!")
                new_state["answer"] = "I encountered an error: Missing action groups for financial analysis"
                new_state["next"] = "format_response"
                return new_state

            try:
                analyzer_result = await analyzer.process_query(processor_state)
                
                for key, value in analyzer_result.items():
                    if key not in ["metadata", "thought_history"]:
                        new_state[key] = value
            except Exception as e:
                logger.error(f"Error in analyzer.process_query: {str(e)}", exc_info=True)
                raise
        
        if new_state.get("requires_tool", False):
            return_control_info = new_state.get("return_control_info", {})
            
            function_info = extract_function_info(return_control_info)
            function_name = function_info.get("function", "")
            action_group = function_info.get("actionGroup", "")
            parameters = extract_parameters(function_info)
            
            new_state["tool_execution"] = {
                "function": function_name,
                "action_group": action_group,
                "parameters": parameters,
                "server_url": tool_server_mapping.get(function_name)
            }
            new_state["next"] = "tool_executor"
        elif new_state.get("answer"):
            new_state["next"] = "format_response"
            log_thought(
                session_id=session_id,
                type="thought",
                category="result",
                node="Answer",
                content=new_state["answer"]
            )
            
            result_thought = {
                "type": "thought",
                "category": "result",
                "node": "Answer",
                "content": new_state["answer"]
            }
            
            if "thought_history" not in new_state:
                new_state["thought_history"] = []
            new_state["thought_history"].append(result_thought)
        else:
            new_state["answer"] = "No response was generated"
            new_state["next"] = "format_response"
    
    except Exception as e:
        logger.error(f"Error in reasoning: {str(e)}")
        new_state["answer"] = f"I encountered an error during analysis: {str(e)}"
        new_state["next"] = "format_response"
        
        error_thought = {
            "type": "thought",
            "category": "error",
            "node": "Reasoning",
            "content": "Error occurred during analysis",
            "technical_details": {"error": str(e)}
        }
        
        log_thought(
            session_id=session_id,
            type="thought",
            category="error",
            node="Reasoning",
            content="Error occurred during analysis",
            technical_details={"error": str(e)}
        )
        
        if "thought_history" not in new_state:
            new_state["thought_history"] = []
        new_state["thought_history"].append(error_thought)
    
    if "tool_result" in new_state:
        del new_state["tool_result"]
    if "tool_error" in new_state:
        del new_state["tool_error"]
    
    return new_state

def extract_function_info(return_control_info):
    """Extract function info from return control event"""
    if "functionResult" in return_control_info:
        return return_control_info["functionResult"]
    
    if "invocationInputs" in return_control_info:
        for input_item in return_control_info["invocationInputs"]:
            if "functionInvocationInput" in input_item:
                return input_item["functionInvocationInput"]
    
    return {}

def extract_parameters(function_info):
    """Extract parameters from function info object"""
    parameters = {}
    
    # Handle different parameter formats
    if "parameters" in function_info:
        # Direct parameter object
        if isinstance(function_info["parameters"], dict):
            parameters = function_info["parameters"]
        # List of name-value pairs
        elif isinstance(function_info["parameters"], list):
            for param in function_info["parameters"]:
                if isinstance(param, dict) and "name" in param and "value" in param:
                    parameters[param["name"]] = param["value"]
    
    return parameters
