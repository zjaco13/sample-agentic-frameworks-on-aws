import os
import streamlit as st
import boto3
import json

# Add these environment variables before the Streamlit imports
os.environ['STREAMLIT_SERVER_PORT'] = '8501'
os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'

# Page config
st.set_page_config(
    page_title="Cloud Support Assistant",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize AWS clients
region = os.getenv('AWS_REGION', 'us-east-1')
agentcore_client = boto3.client(
    'bedrock-agentcore',
    region_name=region
)

def get_agent_arn_from_file():
    """
    Reads the agent ARN from the agent_arn.txt file.
    
    Returns:
        str: The agent ARN if file exists and is readable, None otherwise
    """
    try:
        with open('agent_arn.txt', 'r') as f:
            agent_arn = f.read().strip()
            if agent_arn:
                return agent_arn
            else:
                st.error("Error: agent_arn.txt is empty")
                return None
    except FileNotFoundError:
        st.error("Error: agent_arn.txt not found. Please run deploy_support_agent.py first.")
        return None
    except Exception as e:
        st.error(f"Error reading agent_arn.txt: {e}")
        return None
    
def call_agentcore(prompt):
    """Call AgentCore using AWS Bedrock Agent runtime"""
    agent_arn = get_agent_arn_from_file()
    if not agent_arn:
        return "Error: Could not retrieve agent ARN. Please ensure agent_arn.txt exists and contains a valid ARN."
    
    try:
        payload = json.dumps({"prompt": prompt})
        
        # Debug info
        st.write(f"🔍 Debug: Using region: {region}")
        st.write(f"🔍 Debug: Agent ARN: {agent_arn[:50]}...")
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            qualifier="DEFAULT",
            payload=payload
        )
        
        st.write(f"🔍 Debug: Response content type: {response.get('contentType', 'Unknown')}")
        
        if "text/event-stream" in response.get("contentType", ""):
            content = []
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                        try:
                            data = json.loads(line)
                            if isinstance(data, dict):
                                event = data.get('event', '')
                                contentBlockDelta = event.get('contentBlockDelta', '')
                                delta = contentBlockDelta.get('delta', '')
                                text = delta.get('text', '')
                                content.append(text)
                        except Exception as e:
                            st.write(f"🔍 Debug: Error parsing stream data: {e}")
            result = ''.join(content)
            st.write(f"🔍 Debug: Streaming response length: {len(result)}")
            return result
        
        elif response.get("contentType") == "application/json":
            content = []
            for chunk in response.get("response", []):
                content.append(chunk.decode('utf-8'))
            result = json.loads(''.join(content))
            st.write(f"🔍 Debug: JSON response received")
            return str(result)
        
        else:
            st.write(f"🔍 Debug: Raw response: {response}")
            return str(response)
            
    except Exception as e:
        error_msg = f"Error invoking agent: {str(e)}"
        st.error(error_msg)
        return error_msg

def main():
    # Sidebar
    st.sidebar.title("Cloud Support Assistant")
    
    # Status check
    agent_arn = get_agent_arn_from_file()
    if agent_arn:
        st.sidebar.success("✅ Agent ARN loaded successfully")
        st.sidebar.write(f"Region: {region}")
    else:
        st.sidebar.error("❌ Agent ARN not found")
    
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
                response = call_agentcore(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

    # Clear chat button
    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if __name__ == "__main__":
    main()
