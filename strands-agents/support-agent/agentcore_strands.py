import os
from strands import Agent
from strands.models import BedrockModel
from strands_tools import retrieve
from limit_increase_tool import increase_limit
from view_limits_tool import view_customer_limits
from billing_adjust_tool import adjust_billing
from view_billing_tool import view_customer_billing
from payment_issue_tool import resolve_payment_issue
from refund_processing_tool import process_refund
from customer_feedback_tool import manage_customer_feedback
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Get the KB ID
def get_kb_id():
    with open('kb_id.txt', 'r') as f:
        return f.read().strip()

# Configuration
REGION = 'us-east-1'
KB_ID = get_kb_id()
os.environ['KNOWLEDGE_BASE_ID'] = KB_ID
# Initialize the Bedrock model
model = BedrockModel(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    region_name=REGION
)



system_prompt = """You are a customer support agent for a cloud services company.
Your tasks include:
1. Assisting customers with limit increase requests
2. Providing information about current limits
3. Adjusting billing amounts when necessary
4. Viewing customer billing records
5. Resolving payment issues
6. Processing refund requests and providing refund status updates
7. Collecting and managing customer feedback
8. Answering technical and troubleshooting questions using the knowledge base

For technical support and troubleshooting:
- First check the knowledge base using the retrieve tool
- Provide clear, step-by-step solutions from the documentation
- If the knowledge base doesn't have relevant information, clearly state that

For all other requests:
- Use the appropriate tools to handle customer requests
- Always verify customer information before making changes
- Provide clear confirmation of actions taken

Use the provided tools to help customers with their requests."""

# Initialize the agent with all tools including retrieve
agent = Agent(
    model=model,
    system_prompt=system_prompt,
    tools=[
        retrieve,
        increase_limit,
        view_customer_limits,
        adjust_billing,
        view_customer_billing,
        resolve_payment_issue,
        process_refund,
        manage_customer_feedback
    ],
)
app = BedrockAgentCoreApp()

@app.entrypoint
def invoke_agent(payload):
    user_input = payload.get("prompt")
    response = agent(user_input)
    return response

    

if __name__ == "__main__":
    # Run the AgentCore app
    app.run()
