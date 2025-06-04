import base64
import json
import uuid
import boto3
from typing import Any, AsyncIterable, Dict, List

from common.client import A2ACardResolver
from common.types import AgentCard, TaskSendParams, Message, TextPart, TaskState, Task, Part, DataPart
from hosts.bedrock.remote_agent_connection import TaskUpdateCallback, RemoteAgentConnections


class BedrockHostAgent:
    """An agent that uses Amazon Bedrock for inference."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(
            self,
            model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
            name: str = "bedrock_coordination_agent",
            description: str = "",
            instructions: str = "",
            tools: List[Any] = None,
            is_host_agent: bool = False,
            remote_agent_addresses: List[str] = None,
            task_callback: TaskUpdateCallback | None = None
    ):
        """
        Initializes the Bedrock agent with the given parameters.
        """
        self.model_id = model_id
        self.name = name
        self.description = description
        self.instructions = instructions
        self.tools = tools or []
        self.bedrock_client = boto3.client('bedrock-runtime')
        self.sessions = {}
        self.task_callback = task_callback
        
        # Host agent specific setup
        if is_host_agent and remote_agent_addresses:
            self.remote_agent_connections = {}
            self.cards = {}
            for address in remote_agent_addresses:
                print(f'loading remote agent {address}')
                card_resolver = A2ACardResolver(address)
                print(f'loaded card resolver for {card_resolver.base_url}')
                card = card_resolver.get_agent_card()
                remote_connection = RemoteAgentConnections(card)
                self.remote_agent_connections[card.name] = remote_connection
                self.cards[card.name] = card
            
            self.is_host_agent = True
            self.instructions = self.root_instruction()
        else:
            self.remote_agent_connections = {}
            self.cards = {}
            self.is_host_agent = False

    def invoke(self, query, session_id) -> Dict[str, Any]:
        """
        Invokes the agent with the given query and session ID.
        """
        try:
            # Initialize session if needed
            if session_id not in self.sessions:
                self.sessions[session_id] = []
            
            # Add user message to history
            self.sessions[session_id].append({"role": "user", "content": query})
            
            # If host agent, include agent information in prompt
            if self.is_host_agent:
                response = self._invoke_host_agent(query, session_id)
            else:
                response = self._invoke_regular_agent(query, session_id)
            
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response
            }
        except Exception as e:
            error_message = f"Error invoking agent: {str(e)}"
            print(error_message)
            return {
                "is_task_complete": True,
                "require_user_input": True,
                "content": error_message
            }

    async def stream(self, query, session_id) -> AsyncIterable[Dict[str, Any]]:
        """
        Streams the response from the agent.
        """
        # First yield a processing message
        yield {
            "content": "Processing your request...",
            "is_task_complete": False,
            "require_user_input": False
        }
        
        # Then yield the final result
        result = self.invoke(query, session_id)
        yield result

    def _invoke_regular_agent(self, query, session_id):
        """Handle regular agent invocation"""
        messages = self.sessions[session_id]
        
        # Create payload based on model
        if self.model_id.startswith("anthropic.claude"):
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": messages,
                "system": self.instructions
            }
        else:
            # Default to Claude format
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": messages,
                "system": self.instructions
            }
        
        # Call Bedrock
        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Add assistant response to history
        self.sessions[session_id].append({"role": "assistant", "content": content})
        
        return content

    def _invoke_host_agent(self, query, session_id):
        """Handle host agent invocation with tool calling"""
        # First try to determine which agent to use
        agent_selection_prompt = f"""You are a expert delegator that can delegate user requests to remote agents.
        
Available agents:
{self._format_agent_list()}

Based on the user query: "{query}"
Which agent would be best to handle this request? Respond with just the agent name."""
        
        # Get agent selection
        agent_name = self._get_agent_selection(agent_selection_prompt)
        
        # If we have a valid agent, send the task
        if agent_name and agent_name in self.remote_agent_connections:
            try:
                task_id = str(uuid.uuid4())
                request = TaskSendParams(
                    id=task_id,
                    sessionId=session_id,
                    message=Message(
                        role="user",
                        parts=[TextPart(text=query)],
                        metadata={"conversation_id": session_id},
                    ),
                    acceptedOutputModes=self.SUPPORTED_CONTENT_TYPES,
                    metadata={"conversation_id": session_id},
                )
                
                # Use asyncio to run the async function
                import asyncio
                task = asyncio.run(self.remote_agent_connections[agent_name].send_task(request, self.task_callback))
                
                # Process response
                response = f"I've delegated your request to {agent_name}.\n\n"
                
                if task.status.message:
                    for part in task.status.message.parts:
                        if part.type == "text":
                            response += part.text
                
                if task.artifacts:
                    for artifact in task.artifacts:
                        for part in artifact.parts:
                            if part.type == "text":
                                response += part.text
                
                return response
            except Exception as e:
                return f"Error delegating to {agent_name}: {str(e)}"
        else:
            return f"I couldn't find a suitable agent to handle your request. Available agents are: {', '.join(self.remote_agent_connections.keys())}"

    def _get_agent_selection(self, prompt):
        """Get agent selection from Bedrock"""
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read())
        agent_name = response_body['content'][0]['text'].strip()
        
        # Clean up response to just get the agent name
        for card_name in self.cards.keys():
            if card_name.lower() in agent_name.lower():
                return card_name
        
        return None

    def _format_agent_list(self):
        """Format agent list for prompt"""
        if not self.remote_agent_connections:
            return "No agents available."
        
        agent_info = []
        for card in self.cards.values():
            agent_info.append(f"- {card.name}: {card.description}")
        
        return "\n".join(agent_info)

    def register_agent_card(self, card: AgentCard):
        """Register a new agent card"""
        remote_connection = RemoteAgentConnections(card)
        self.remote_agent_connections[card.name] = remote_connection
        self.cards[card.name] = card

    def root_instruction(self) -> str:
        """Root instruction for host agent"""
        return f"""You are an expert delegator that can delegate user requests to the appropriate remote agents.

Available agents:
{self._format_agent_list()}

Your job is to:
1. Understand the user's request
2. Determine which agent is best suited to handle it
3. Delegate the task to that agent
4. Return the agent's response to the user

Always identify which agent you're using in your response.
"""

    def list_remote_agents(self):
        """List available remote agents"""
        if not self.remote_agent_connections:
            return []

        remote_agent_info = []
        for card in self.cards.values():
            remote_agent_info.append(
                {"name": card.name, "description": card.description}
            )
        return remote_agent_info
