from typing import Any, Dict, AsyncIterable, List
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
import json
from typing import TypedDict, Annotated

memory = MemorySaver()

# Define a proper state schema
class AgentState(TypedDict):
    messages: List[Any]

class LangraphBedrockAgent:
    def __init__(self):
        # Initialize tools
        self.tavily_search = TavilySearchResults()
        self.wikipedia_query_runner = WikipediaQueryRun(
            api_wrapper=WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100)
        )
        
        # Initialize Bedrock model
        self.model = ChatBedrock(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0")
        
        # Define tools
        self.tools = [self.tavily_search, self.wikipedia_query_runner]
        
        # Create the agent graph
        self.graph = self.build_graph()
        
        # Agent instruction
        self.agent_instruction = """You are a helpful AI assistant that provides users with latest updates in Generative Ai."""

    def build_graph(self):
        # Build the graph with proper state schema
        graph = StateGraph(AgentState)
        
        # Define the agent node
        def agent_node(state: AgentState):
            messages = state["messages"]
            
            # Add system message with instructions
            if not any(isinstance(m, AIMessage) for m in messages):
                messages = [
                    HumanMessage(content=self.agent_instruction),
                    *messages
                ]
            
            # Call the model
            response = self.model.invoke(messages)
            
            # Check if the response contains tool calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                return {"messages": messages + [response], "next": "tools"}
            
            # If no tool calls, we're done
            return {"messages": messages + [response], "next": END}
        
        # Define the tools node
        def tools_node(state: AgentState):
            messages = state["messages"]
            last_message = messages[-1]
            
            # Process each tool call
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = json.loads(tool_call["args"])
                
                # Find the right tool
                for tool in self.tools:
                    if tool.name == tool_name:
                        # Execute the tool
                        result = tool.invoke(tool_args)
                        # Add the result as a tool message
                        messages.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call["id"],
                                name=tool_name,
                            )
                        )
            
            return {"messages": messages, "next": "agent"}
        
        # Add nodes
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tools_node)
        
        # Add edges - including the START edge
        graph.add_edge(START, "agent")
        graph.add_edge("agent", "tools")
        graph.add_edge("tools", "agent")
        
        # Compile the graph
        return graph.compile(checkpointer=memory)

    def invoke(self, query, sessionId) -> Dict[str, Any]:
        try:
            config = {"configurable": {"thread_id": sessionId}}
            result = self.graph.invoke(
                {"messages": [HumanMessage(content=query)]}, 
                config
            )
            
            # Get the final message
            final_message = result["messages"][-1]
            
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": final_message.content
            }
        except Exception as e:
            agent_reply = f"Error invoking agent: {e}"
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": agent_reply
            }

    async def stream(self, query, sessionId) -> AsyncIterable[Dict[str, Any]]:
        config = {"configurable": {"thread_id": sessionId}}
        inputs = {"messages": [HumanMessage(content=query)]}
        
        for chunk in self.graph.stream(inputs, config, stream_mode="values"):
            messages = chunk["messages"]
            last_message = messages[-1]
            
            if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls") and last_message.tool_calls:
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Searching for information..."
                }
            elif isinstance(last_message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": f"Processing information from {last_message.name}..."
                }
            elif isinstance(last_message, AIMessage):
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": last_message.content
                }
        
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
