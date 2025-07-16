import os
import streamlit as st
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


# Add these environment variables before the Streamlit imports
os.environ['STREAMLIT_SERVER_PORT'] = '8501'
os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'

# Page config
st.set_page_config(
    page_title="Cloud Support Assistant",
    page_icon="☁️",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

def initialize_agent():
    """Initialize the Strands agent with all tools"""
    
    # Read KB ID from file and set it as environment variable
    with open('kb_id.txt', 'r') as f:
        kb_id = f.read().strip()
    os.environ['KNOWLEDGE_BASE_ID'] = kb_id

    # Initialize the Bedrock model
    model = BedrockModel(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        region_name="us-east-1"
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

    # Initialize the agent with all tools
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
    return agent


def main():
    # Sidebar
    st.sidebar.title("Cloud Support Assistant")
    st.sidebar.markdown("""
    This assistant can help you with:
    - Technical troubleshooting
    - Limit increases
    - Billing adjustments
    - Payment issues
    - Refund requests
    - Customer feedback
    """)
    
    # Example queries in sidebar
    st.sidebar.markdown("### Example Queries")
    example_queries = [
        "How can I improve storage upload performance?",
        "I need to increase my API call limit to 3000. My customer ID is CUST_001",
        "Can you check my current limits? My customer ID is CUST_002",
        "I need to update my credit card. My customer ID is CUST_001",
        "What's the status of my refund request? My customer ID is CUST_003"
    ]
    
    for query in example_queries:
        if st.sidebar.button(query):
            st.session_state.messages.append({"role": "user", "content": query})

    # Main chat interface
    st.title("Cloud Support Chat")

    # Initialize agent
    agent = initialize_agent()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("How can I help you today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = agent(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

    # Clear chat button
    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if __name__ == "__main__":
    main()
