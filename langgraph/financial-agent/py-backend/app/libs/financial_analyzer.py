import json
import logging
import boto3
import uuid
import datetime
from typing import Dict, List, Any, Optional, Callable, TypedDict, Literal, AsyncGenerator
from app.libs.thought_stream import thought_handler
from app.libs.conversation_memory import conversation_memory
from botocore.config import Config
from app.libs.types import GraphState
from app.libs.decorators import log_thought

logger = logging.getLogger(__name__)

class ThoughtCallback(TypedDict):
    type: Literal["thought"]
    category: Literal["setup", "analysis", "tool", "result", "error"]
    content: str
    node: str
    technical_details: Optional[Dict[str, Any]]

class ToolResult(TypedDict):
    action_group: str
    function: str
    result: str | Dict[str, Any]

class FinancialAnalyzer:    
    def __init__(self, model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"):
        self.model_id = model_id
        self.boto_config = Config(
            max_pool_connections=10,  
            connect_timeout=5,
            read_timeout=120,
            retries={"max_attempts": 3}
        )
        self.bedrock_client = boto3.client('bedrock-runtime', config=self.boto_config)
        self.bedrock_agent_client = boto3.client('bedrock-agent-runtime', config=self.boto_config)
        self.session_state = {
            "sessionAttributes": {},
            "promptSessionAttributes": {}
        }
        self._last_return_control_event = None
        self.session_id = str(uuid.uuid4())
        self.app_session_id = None
        self.return_control_info = None
        self.all_action_groups = []
        self.conversation_memory = conversation_memory
        
    def reset_session(self):
        self.session_id = str(uuid.uuid4())
        self.session_state = {
            "sessionAttributes": {},
            "promptSessionAttributes": {}
        }
        self._last_return_control_event = None
        self.return_control_info = None

    def get_session_info(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_state": self.session_state,
            "has_return_control": bool(self._last_return_control_event)
        }

    async def cleanup(self):
        try:
            if hasattr(self.bedrock_client, 'close'):
                await self.bedrock_client.close()
            if hasattr(self.bedrock_agent_client, 'close'):
                await self.bedrock_agent_client.close()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def _track_state_change(self, state: str, details: Dict[str, Any] = None):
        logger.info(f"State change: {state}", extra={
            "state": state,
            "details": details,
            "session_id": self.session_id,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    async def process_query(self, state: GraphState) -> GraphState:
        """Process a query using Bedrock inline agent with state object"""
        new_state = state.copy()
        query = new_state.get("query", "")
        action_groups = new_state.get("action_groups", [])
        instruction = new_state.get("instruction", "")
        session_id = new_state.get("session_id")
        thought_history = new_state.get("thought_history", [])
        
        if not action_groups:
            new_state["error"] = "No valid action groups provided"
            new_state["next"] = "error"
            return new_state
            
        self.all_action_groups = action_groups
        logger.info(f"Storing {len(action_groups)} action groups for future calls")
        self._track_state_change("query_received", {"query": query})
        self.app_session_id = session_id
            
        if session_id:
            self.session_id = session_id 
        else:
            self.session_id = str(uuid.uuid4())
            new_state["session_id"] = self.session_id

        conversation_session_id = self.app_session_id or self.session_id
        inline_session_state = self.conversation_memory.get_bedrock_inline_session_state(conversation_session_id)
        
        if 'invocationId' in inline_session_state:
            del inline_session_state['invocationId']
        
        self.session_state = inline_session_state

        params = {
            'actionGroups': action_groups,
            'foundationModel': self.model_id,
            'inputText': query, 
            'instruction': instruction,  
            'sessionId': self.session_id,
            'inlineSessionState': inline_session_state
        }
        
        debug_params = params.copy()
        if 'inputText' in debug_params:
            debug_params['inputText'] = debug_params['inputText'][:100] + "..." if len(debug_params['inputText']) > 100 else debug_params['inputText']

        logger.info(f"Using Bedrock session ID: {self.session_id}")
        logger.info(f"Request params: actionGroups: {len(action_groups)}, model: {self.model_id}, query length: {len(query)}")        
        try:
            self._track_state_change("invoking_bedrock")
            log_thought(
                session_id=session_id,
                type="thought",
                category="setup",
                node="Financial Analyzer",
                content=f"Invoking AWS Bedrock with query: {query[:100]}..." if len(query) > 100 else query
            )

            response = self.bedrock_agent_client.invoke_inline_agent(**params)
            result = await self._process_response(response, instruction)
            
            for key, value in result.items():
                new_state[key] = value
                
            if result.get("requires_tool", False):
                new_state["next"] = "execute_tool"
                new_state["tool_execution"] = result.get("tool_execution", {})
            else:
                new_state["next"] = "complete"
                
            return new_state
            
        except Exception as e:
            logger.error(f"Bedrock invocation error: {e}")
            log_thought(
                session_id=session_id,
                type="thought",
                category="error",
                node="Financial Analyzer",
                content=f"Error invoking Bedrock: {str(e)}"
            )
            new_state["error"] = str(e)
            new_state["next"] = "error"
            return new_state

    async def _process_response(self, response, instruction) -> Dict[str, Any]:
        if response.get('ResponseMetadata', {}).get('HTTPStatusCode') != 200:
            return self._create_error_response("API returned non-200 status code")
        
        response_chunks = []
        self.return_control_info = None
        try:
            async for chunk in self._process_chunks(response["completion"]):
                response_chunks.append(chunk)
            
            self._track_state_change("processing_response")
            
            if self.return_control_info:
                rationale_content = self.latest_rationale or "Tool execution required"
                logger.info(f"Using rationale for thought: {rationale_content}")   
                
                action_group = ""
                function = "unknown"
                parameters = {}
                server_url = ""
                
                if "invocationInputs" in self.return_control_info:
                    invocation_inputs = self.return_control_info["invocationInputs"]
                    if invocation_inputs and len(invocation_inputs) > 0:
                        func_input = invocation_inputs[0].get("functionInvocationInput", {})
                        
                        action_group = func_input.get("actionGroup", "")
                        function = func_input.get("function", "unknown")
                        raw_parameters = func_input.get("parameters", [])
                        
                        parameters = {}
                        for param in raw_parameters:
                            if isinstance(param, dict) and "name" in param and "value" in param:
                                parameters[param["name"]] = param["value"]
                        
                        if action_group:
                            if "_" in action_group:
                                parts = action_group.split("_")
                                if len(parts) >= 3:
                                    host = parts[0]
                                    port = parts[1]
                                    server_url = f"http://{host}:{port}"
                
                tool_execution_info = {
                    "action_group": action_group,
                    "function": function,
                    "parameters": parameters,
                    "server_url": server_url
                }
                
                self.conversation_memory.add_tool_usage_message(
                    self.app_session_id, 
                    function,
                    parameters
                )
                
                return {
                    "requires_tool": True,
                    "return_control_info": self.return_control_info,
                    "tool_execution": tool_execution_info,
                    "invocation_id": self._extract_invocation_id(self.return_control_info)
                }
            
            if response_chunks:
                combined_response = "".join(response_chunks).strip()
                
                self.conversation_memory.add_assistant_message(
                    self.app_session_id,
                    combined_response,
                    source="inline_agent"
                )
                
                return {
                    "requires_tool": False,
                    "answer": combined_response,
                    "text_chunks": response_chunks
                }
                
            return self._create_error_response("No response generated")
            
        except Exception as e:
            logger.error(f"Response processing error: {e}")
            return self._create_error_response(str(e))

    async def _process_chunks(self, completion) -> AsyncGenerator[str, None]:
        self.return_control_info = None
        self.latest_rationale = None
        
        all_events = list(completion)
        
        return_control_event = None
        trace_events = []
        chunks = []
        
        for event in all_events:
            if "returnControl" in event:
                return_control_event = event
                self.return_control_info = event["returnControl"]
            elif "returnControlInvocation" in event:
                return_control_event = event
                self.return_control_info = event["returnControlInvocation"]
            elif "trace" in event:
                trace_events.append(event)
            elif "chunk" in event and "bytes" in event["chunk"]:
                chunks.append(event)
            elif "sessionState" in event:                
                self.session_state = event["sessionState"]
        
        for event in trace_events:
            # self._process_thinking_trace(event)
            try:
                trace_data = event.get('trace', {}).get('trace', {})
                if "orchestrationTrace" in trace_data and "rationale" in trace_data["orchestrationTrace"]:
                    self.latest_rationale = trace_data["orchestrationTrace"]["rationale"]["text"]
                    logger.info(f"Found rationale text: {self.latest_rationale}...")
            except Exception as e:
                logger.error(f"Error extracting rationale: {e}")
        
        for event in chunks:
            try:
                chunk_text = event["chunk"]["bytes"].decode('utf-8')
                yield chunk_text
            except Exception as e:
                logger.error(f"Chunk decoding error: {e}")

    def _extract_invocation_id(self, return_control_info):
        if "invocationId" in return_control_info:
            return return_control_info["invocationId"]
        
        if "functionResult" in return_control_info and "invocationId" in return_control_info["functionResult"]:
            return return_control_info["functionResult"]["invocationId"]
        
        return None
    
    def _process_thinking_trace(self, event):
        try:
            trace_json = event.get('trace', {})
            if not trace_json or "trace" not in trace_json:
                return
                
            trace_data = trace_json["trace"]
            thought_content = ""
            thought_category = "analysis"
            technical_details = {}
            
            if "orchestrationTrace" in trace_data and "rationale" in trace_data["orchestrationTrace"]:
                thought_content = trace_data["orchestrationTrace"]["rationale"]["text"]
                
            elif "orchestrationTrace" in trace_data and "modelInvocationOutput" in trace_data["orchestrationTrace"]:
                model_output = trace_data["orchestrationTrace"]["modelInvocationOutput"]
                
                if "metadata" in model_output and "usage" in model_output["metadata"]:
                    technical_details["input_tokens"] = model_output["metadata"]["usage"].get("inputTokens", 0)
                    technical_details["output_tokens"] = model_output["metadata"]["usage"].get("outputTokens", 0)
                
                if "rawResponse" in model_output:
                    raw_response = model_output["rawResponse"]
                    if isinstance(raw_response, dict) and "content" in raw_response:
                        technical_details["raw_thinking"] = str(raw_response["content"])
                
            if "orchestrationTrace" in trace_data and "observation" in trace_data["orchestrationTrace"]:
                observation = trace_data["orchestrationTrace"]["observation"]
                
                if "actionGroupInvocationOutput" in observation:
                    thought_category = "tool"
                    tool_output = observation["actionGroupInvocationOutput"].get("text", "")
                    technical_details["tool_output"] = tool_output
                    if not thought_content:
                        thought_content = f"Tool execution result: {tool_output}"
            
            if "failureTrace" in trace_data:
                thought_category = "error"
                failure_reason = trace_data["failureTrace"].get("failureReason", "Unknown failure")
                thought_content = f"Error occurred: {failure_reason}"
            
            if "guardrailTrace" in trace_data:
                guardrail_data = trace_data["guardrailTrace"]
                if guardrail_data.get("action") == "INTERVENED":
                    thought_category = "analysis"
                    thought_content = "Guardrail intervention occurred"
                    technical_details["guardrail"] = {
                        "input_assessments": guardrail_data.get("inputAssessments", []),
                        "output_assessments": guardrail_data.get("outputAssessments", [])
                    }
                
            if thought_content:
                log_thought(
                    session_id=self.app_session_id,
                    type="thought",
                    category=thought_category,
                    node="Financial Analyzer",
                    content=thought_content,
                    technical_details=technical_details
                )

        except Exception as e:
            logger.error(f"Error processing thinking trace: {e}")
            log_thought(
                session_id=self.app_session_id,
                type="thought",
                category="error",
                content=f"Error extracting thinking process: {str(e)}",
                node="Financial Analyzer"
            )
    
    async def process_tool_result(self, state: GraphState) -> GraphState:
        new_state = state.copy()
        tool_result = new_state.get("tool_result", {})
        instruction = new_state.get("instruction", "")
        invocation_id = new_state.get("invocation_id")
        thought_history = new_state.get("thought_history", [])
        tool_error = new_state.get("tool_error")
        session_id = new_state.get("session_id")
        
        self.app_session_id = session_id
        self.conversation_memory.add_tool_result_message(
            session_id, 
            tool_result.get('function', 'unknown'), 
            tool_result.get('result', '')
        )
        
        if tool_error:
            log_thought(
                session_id=session_id,
                type="thought",
                category="error",
                node="Financial Analyzer",
                content="Tool execution failed. Continuing with analysis.",
                technical_details={"error": tool_error}
            )
            
            if invocation_id:
                function_result_object = {
                    "actionGroup": tool_result.get('action_group', 'unknown'),
                    "function": tool_result.get('function', 'unknown'),
                    "agentId": "INLINE_AGENT",
                    "responseBody": {
                        "TEXT": {"body": f"Error: {tool_error}"}
                    },
                    "responseState": "FAILURE"
                }
                
                params = self._prepare_continuation_params(
                    invocation_id, 
                    function_result_object, 
                    instruction
                )
                
                try:
                    logger.info("Processing tool error result")
                    response = self.bedrock_agent_client.invoke_inline_agent(**params)
                    result = await self._process_response(response, instruction)
                    
                    for key, value in result.items():
                        new_state[key] = value
                        
                    if result.get("requires_tool", False):
                        new_state["next"] = "execute_tool"
                        new_state["tool_execution"] = result.get("tool_execution", {})
                    else:
                        new_state["next"] = "complete"
                        
                    return new_state
                    
                except Exception as e:
                    logger.error(f"Tool error handling failed: {e}")
                    log_thought(
                        session_id=session_id,
                        type="thought",
                        category="error",
                        node="Financial Analyzer",
                        content=f"Error handling tool failure: {str(e)}"
                    )
                    new_state["error"] = f"Tool error handling failed: {str(e)}"
                    new_state["next"] = "error"
                    return new_state
        
        if not invocation_id:
            invocation_id = self._get_invocation_id_from_last_event()
            
        if not invocation_id:
            log_thought(
                session_id=session_id,
                type="thought",
                category="error",
                node="Financial Analyzer",
                content="Missing invocation ID for tool result processing"
            )
            new_state["error"] = "Missing invocation ID"
            new_state["next"] = "error"
            return new_state
        
        function_result_object = self._format_function_result(tool_result)
        
        params = self._prepare_continuation_params(
                invocation_id, 
                function_result_object, 
                instruction
            )
        
        try:
            self._track_state_change("tool_result_processing", {"function": tool_result['function']})
            log_thought(
                session_id=session_id,
                type="thought",
                category="tool",
                node="Financial Analyzer",
                content=f"Processing result from {tool_result['function']}",
                technical_details={"result_preview": str(tool_result['result'])[:100] + "..." if isinstance(tool_result['result'], str) and len(str(tool_result['result'])) > 100 else str(tool_result['result'])}
            )

            response = self.bedrock_agent_client.invoke_inline_agent(**params)
            result = await self._process_response(response, instruction)
            
            for key, value in result.items():
                new_state[key] = value
                
            if result.get("requires_tool", False):
                new_state["next"] = "execute_tool"
                tool_execution = result.get("tool_execution", {})
                new_state["tool_execution"] = result.get("tool_execution", {})
            else:
                new_state["next"] = "complete"
                
            return new_state
            
        except Exception as e:
            logger.error(f"Tool result processing error: {e}", exc_info=True)
            log_thought(
                session_id=session_id,
                type="thought",
                category="error",
                node="Financial Analyzer",
                content=f"Error processing tool result: {str(e)}"
            )
            new_state["error"] = str(e)
            new_state["next"] = "error"
            return new_state


    def _get_invocation_id_from_last_event(self) -> Optional[str]:
        if not self._last_return_control_event:
            return None
            
        if 'returnControl' in self._last_return_control_event:
            return self._last_return_control_event['returnControl'].get('invocationId')
        
        if 'returnControlInvocation' in self._last_return_control_event:
            return self._last_return_control_event['returnControlInvocation'].get('invocationId')
            
        return None

    def _prepare_continuation_params(self, 
                                invocation_id: str, 
                                function_result: Dict[str, Any],
                                instruction: str) -> Dict[str, Any]:
        session_state = {
            'invocationId': invocation_id,
            'returnControlInvocationResults': [
                {'functionResult': function_result}
            ]
        }
        
        if self.session_state and 'sessionAttributes' in self.session_state:
            session_state['sessionAttributes'] = self.session_state.get('sessionAttributes', {})
            
        if self.session_state and 'promptSessionAttributes' in self.session_state:
            session_state['promptSessionAttributes'] = self.session_state.get('promptSessionAttributes', {})
        
        params = {
            'actionGroups': self.all_action_groups,
            'foundationModel': self.model_id,
            'sessionId': self.session_id,
            'inputText': '',
            'instruction': instruction,
            'enableTrace': True,
            'inlineSessionState': session_state
        }
        return params
    
    def _format_function_result(self, tool_result: ToolResult) -> Dict[str, Any]:
        result_content = (json.dumps(tool_result['result']) 
                         if not isinstance(tool_result['result'], str) 
                         else tool_result['result'])
        
        return {
            "actionGroup": tool_result['action_group'],
            "function": tool_result['function'],
            "agentId": "INLINE_AGENT",
            "responseBody": {
                "TEXT": {"body": result_content}
            }
        }
        
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        logger.error(f"Creating error response: {error_message}")
        self._track_state_change("error", {"message": error_message})
        log_thought(
            session_id=self.app_session_id,
            type="thought",
            category="error",
            node="Financial Analyzer",
            content=f"Error: {error_message}"
        )
        return {
            'requires_tool': False,
            'output': {
                'message': {
                    'content': [{'text': error_message}]
                }
            },
            'answer': error_message,
            'text_chunks': [error_message]
        }
