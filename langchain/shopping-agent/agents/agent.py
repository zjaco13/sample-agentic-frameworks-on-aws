from typing import Annotated, List,NotRequired
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from langchain.messages import SystemMessage, HumanMessage, AIMessage

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.managed.is_last_step import RemainingSteps
from langgraph.types import interrupt

from agents.subagents import invoice_subagent, opensearch_subagent
from agents.opensearch_memory_client import get_memory_client
from agents.prompts import (
    supervisor_routing_prompt,
    supervisor_system_prompt,
    extract_customer_info_prompt,
    verify_customer_info_prompt,
    create_memory_prompt
)
from agents.utils import (
    llm, 
    get_customer_id_from_identifier,
    format_user_memory
)


# ------------------------------------------------------------
# State Schema
# ------------------------------------------------------------
class InputState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

class State(InputState):
    customer_id: NotRequired[str]
    loaded_memory: NotRequired[str]
    next_agent: NotRequired[str]  # For conditional routing


# ------------------------------------------------------------
# Supervisor Router - Decides which agent to route to
# ------------------------------------------------------------
def supervisor_router(state: State) -> dict:
    """
    Supervisor that routes to appropriate subagent using LLM decision.
    Uses conditional routing instead of tools to avoid Bedrock ValidationException.
    """
    messages = state["messages"]

    # Create routing prompt with conversation context
    routing_messages = [
        SystemMessage(content=supervisor_routing_prompt),
        *messages
    ]

    # Get routing decision from LLM
    response = llm.invoke(routing_messages)
    next_agent = response.content.strip()

    print(f"[Supervisor] Routing decision: {next_agent}")

    # Store the routing decision in state
    return {"next_agent": next_agent}

# ------------------------------------------------------------
# Subagent Nodes - Execute specialized tasks
# ------------------------------------------------------------
def invoice_agent_node(state: State) -> dict:
    """Node that executes the invoice subagent."""
    print(f"[Invoice Agent] Processing query")

    # Get only user messages (filter out supervisor routing messages)
    user_messages = [msg for msg in state["messages"] if msg.type in ["human", "user"]]

    # Invoke the invoice subagent with clean message history
    result = invoice_subagent.invoke({
        "messages": user_messages,  # Only user messages, no tool_use artifacts
        "customer_id": state.get("customer_id", ""),
    })

    # Return the subagent's response as new messages
    return {"messages": result["messages"]}

def opensearch_agent_node(state: State) -> dict:
    """Node that executes the opensearch subagent."""
    print(f"[OpenSearch Agent] Processing query")

    # Get only user messages (filter out supervisor routing messages)
    user_messages = [msg for msg in state["messages"] if msg.type in ["human", "user"]]

    # Add customer memory context if available
    loaded_memory = state.get("loaded_memory", "")
    messages_with_context = user_messages.copy()

    if loaded_memory and loaded_memory != "No preferences stored yet":
        # Prepend customer preferences as a system message for the subagent
        memory_context = SystemMessage(
            content=f"""CUSTOMER PROFILE AND PREFERENCES:
{loaded_memory}

Use these preferences to personalize product recommendations and filter search results.
Prioritize products matching the customer's favorite colors, sizes, and interests."""
        )
        messages_with_context = [memory_context] + user_messages

    # Invoke the opensearch subagent with clean message history and context
    result = opensearch_subagent.invoke({
        "messages": messages_with_context,
        "customer_id": state.get("customer_id", ""),
        "loaded_memory": loaded_memory
    })

    # Return the subagent's response as new messages
    return {"messages": result["messages"]}

# ------------------------------------------------------------
# Human Feedback Nodes
# ------------------------------------------------------------

# Schema for parsing user-provided account information
class UserInput(BaseModel):
    identifier: str = Field(description = "Identifier, which can be a customer ID, email, or phone number.")

def verify_info(state: State):
    """Verify the customer's account by parsing their input and matching it with the database."""
    if state.get("customer_id") is None: 
        user_input = state["messages"][-1] 
        # Parse for customer ID
        parsed_info = llm.with_structured_output(schema=UserInput).invoke([SystemMessage(content=extract_customer_info_prompt)] + [user_input])
        # Extract details
        identifier = parsed_info.identifier
        customer_id = ""

        if (identifier):
            customer_id = get_customer_id_from_identifier(identifier)
        if customer_id != "":
            intent_message = AIMessage(
                content= f"Thank you for providing your information! I was able to verify your account with customer id {customer_id}."
            )
            return {"customer_id": customer_id, "messages" : [intent_message]}
        else:
          response = llm.invoke([SystemMessage(content=verify_customer_info_prompt)]+state['messages'])
          return {"messages": [response]}
    else: 
        pass

def human_input(state: State):
    """ No-op node that should be interrupted on """
    user_input = interrupt("Please provide input.")
    return {"messages": [HumanMessage(content=user_input)]}

# Edge Condition for interrupts
def should_interrupt(state: State):
    if state.get("customer_id") is not None:
        return "continue"
    else:
        return "interrupt"


# ------------------------------------------------------------
# Long Term Memory Nodes - Using OpenSearch Agentic Memory
# ------------------------------------------------------------

def load_memory(state: State):
    """Loads music preferences from users using OpenSearch agentic memory."""
    user_id = state["customer_id"]
    formatted_memory = ""

    try:
        # Get memory client (uses OPENSEARCH_MEMORY_CONTAINER_ID from env)
        memory_client = get_memory_client()

        # Retrieve customer memory from OpenSearch
        existing_memory = memory_client.get_customer_memory(customer_id=user_id)

        if existing_memory and existing_memory.get('preferences'):
            # Format the memory for use in the agent
            formatted_memory = format_user_memory({"memory": existing_memory['preferences']})
            print(f"[Memory] Loaded preferences for customer {user_id}")
        else:
            print(f"[Memory] No existing preferences found for customer {user_id}")

    except Exception as e:
        print(f"[Memory] Error loading memory: {e}")
        # Gracefully degrade - continue without memory

    return {"loaded_memory": formatted_memory}

# User profile structure for creating memory
class UserProfile(BaseModel):
    customer_id: str = Field(description="The customer ID of the customer")
    music_preferences: List[str] = Field(
        default_factory=list,
        description="The music preferences of the customer (e.g., rock, jazz, classical)"
    )
    favorite_colors: List[str] = Field(
        default_factory=list,
        description="The customer's favorite colors for clothing and products (e.g., blue, black, red)"
    )
    dress_size: str = Field(
        default="",
        description="The customer's dress/clothing size (e.g., S, M, L, XL, or numeric sizes)"
    )
    shoe_size: str = Field(
        default="",
        description="The customer's shoe size (e.g., 8, 9, 10, or EU sizes)"
    )
    style_preferences: List[str] = Field(
        default_factory=list,
        description="The customer's style preferences (e.g., casual, formal, athletic, vintage)"
    )
    interests: List[str] = Field(
        default_factory=list,
        description="General interests and hobbies (e.g., hiking, cooking, gaming, reading)"
    )

def create_memory(state: State):
    """Updates customer preferences using OpenSearch agentic memory."""
    user_id = str(state["customer_id"])
    formatted_memory = state.get("loaded_memory", "")

    try:
        # Get memory client (uses OPENSEARCH_MEMORY_CONTAINER_ID from env)
        memory_client = get_memory_client()

        # Use LLM to extract updated preferences from conversation
        formatted_system_message = SystemMessage(
            content=create_memory_prompt.format(
                conversation=state["messages"],
                memory_profile=formatted_memory
            )
        )
        updated_memory = llm.with_structured_output(UserProfile).invoke([formatted_system_message])

        # Convert Pydantic model to dict for storage
        preferences_dict = {
            "customer_id": updated_memory.customer_id,
            "music_preferences": updated_memory.music_preferences,
            "favorite_colors": updated_memory.favorite_colors,
            "dress_size": updated_memory.dress_size,
            "shoe_size": updated_memory.shoe_size,
            "style_preferences": updated_memory.style_preferences,
            "interests": updated_memory.interests
        }

        # Store in OpenSearch agentic memory
        memory_id = memory_client.add_customer_memory(
            customer_id=user_id,
            preferences=preferences_dict
        )

        print(f"[Memory] Updated preferences for customer {user_id} (memory_id: {memory_id})")

    except Exception as e:
        print(f"[Memory] Error creating/updating memory: {e}")
        # Continue even if memory update fails

    return {}


# ------------------------------------------------------------
# State Graph with Conditional Routing
# ------------------------------------------------------------
def route_after_supervisor(state: State) -> str:
    """Route to the appropriate agent based on supervisor's decision."""
    next_agent = state.get("next_agent", "FINISH")
    print(f"[Router] Directing to: {next_agent}")
    return next_agent

workflow_builder = StateGraph(State, input_schema = InputState)

# Add all nodes
workflow_builder.add_node("verify_info", verify_info)
workflow_builder.add_node("human_input", human_input)
workflow_builder.add_node("load_memory", load_memory)
workflow_builder.add_node("supervisor", supervisor_router)  # Router, not agent
workflow_builder.add_node("opensearch_agent", opensearch_agent_node)  # Subagent node
workflow_builder.add_node("invoice_agent", invoice_agent_node)  # Subagent node
workflow_builder.add_node("create_memory", create_memory)

# Build the workflow
workflow_builder.add_edge(START, "verify_info")
workflow_builder.add_conditional_edges(
    "verify_info",
    should_interrupt,
    {
        "continue": "load_memory",
        "interrupt": "human_input",
    },
)
workflow_builder.add_edge("human_input", "verify_info")
workflow_builder.add_edge("load_memory", "supervisor")

# Conditional routing from supervisor to agents
workflow_builder.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {
        "opensearch_agent": "opensearch_agent",
        "invoice_agent": "invoice_agent",
        "FINISH": "create_memory"
    }
)

# Both agents return to create_memory
workflow_builder.add_edge("opensearch_agent", "create_memory")
workflow_builder.add_edge("invoice_agent", "create_memory")
workflow_builder.add_edge("create_memory", END)

# Compile the graph
# LangGraph API (dev or cloud) provides managed persistence automatically.
# Do not use a custom store - the platform handles it.
graph = workflow_builder.compile(name="multi_agent_verify")
