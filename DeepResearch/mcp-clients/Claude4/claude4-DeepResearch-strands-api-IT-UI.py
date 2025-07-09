
#File: claude4-DeepResearch-strands-api-interleavedThinking.py
#Author: Chris Smith
#Email: smithzgg@amazon.com
#Created: 06/15/2025
#Last Modified: 07/03/2025

#Description:
#    Deep Research MCP client using Claude4 built on the Strands
#     framework using the Anthropic API.  This example is single turn
#     to highlighlight the interleaved thinking process Claude 4 demonstrates
#     in-between tool calls.  It uses AWS guardrails to allow for custom restrictions
#      to the model behavoir if needed.

#Usage:
#    \$ python <filename>.py 
    
#Dependencies:
#    - mcp
#    - strands-agents
#    - strands-agents-tools
#    - boto3
#    - anthropic
#    - time

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent, tool
from strands.models.anthropic import AnthropicModel
from strands.tools.mcp.mcp_client import MCPClient
import logging
import boto3
import os
import time
import streamlit as st

DEBUG = 0
#set this variable to the number of deep research questions you want to generate for the research topic
#more questions = more depth, but more processing time and context
#default is 3
NUM_QUESTIONS = "3"
#set to true if you want to include searching internal AWS Knowledge Bases
INTERNAL_SEARCH = "false"
#set to true if you want to use custom AWS Guardrails
USE_GUARDRAILS = "false"


# Get environment

#set AWS_GUARDRAIL_ID and AWS_GUARDRAIL_VERSION if you intend on using AWS Guardrails
if USE_GUARDRAILS.lower() == "true" :
    guardrail_id = os.getenv("AWS_GUARDRAIL_ID")
    guardrail_version = os.getenv("AWS_GUARDRAIL_VERSION")

#Set the MCP Server to the server connect string
# example:  export MCP_SERVER="http://localhost:8000/mcp/" for a local server
# or export MCP_SERVER="http://10.10.10.10:8000/mcp/"   for a remote MCP server

mcp_server=os.getenv("MCP_SERVER")

# Set your Anthropic API KEY.  Go to https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-west-2")

# Enables Strands debug log level
logging.getLogger("strands").setLevel(logging.ERROR)

# Sets the logging format and streams logs to stderr
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

model = AnthropicModel(
    client_args={
        "api_key": anthropic_api_key,
    },
    # **model_config
    max_tokens=8196,
 #   model_id="claude-3-7-sonnet-20250219",
    model_id="claude-sonnet-4-20250514",
    params={
        "temperature": 0.7,
    },
    thinking = {
        "type" : "enabled",
        "budget tokens" : 8000
    },
    extra_headers={
        "anthropic-beta": "interleaved-thinking-2025-05-14"
    }
)

def create_streamable_http_transport():
   return streamablehttp_client(mcp_server)
   
 # Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []  

# function to apply Bedrock Guardrails.  
# Insert any custom Python code for additional guardrails

def apply_bedrock_guardrail(input_text, source):
    
    gr_response = bedrock_runtime.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=guardrail_version,
        source=source,  
        content=[{"text": {"text": input_text}}]
    )
    return gr_response["action"]

def my_callback_handler(**kwargs) :

        if "message" in kwargs and kwargs["message"].get("role") == "assistant" :
            for content in kwargs["message"]["content"] :
                if (USE_GUARDRAILS.lower() == "true") and (apply_bedrock_guardrail(str(content), "INPUT") == "GUARDRAIL_INTERVENED"):

                    st.write("Uh-oh, this question has triggered my internal guardrails due to content restrictions, my answer may not include all the relevant data")
                else:
                    if "text" in content:
                        #print("\n\n------------------------------------")
                        #print(str(kwargs))
                        st.write(f'**Research Assistant:** {content["text"]}')
                        #print("------------------------------------\n")
                    
                    if "toolUse" in content :
                        if str(content["toolUse"]["name"]) == "tavily_web_search" :
                            st.write(f'\n**Research Assistant:** Doing a web search on {content["toolUse"]["input"]["question"]}')
                        elif str(content["toolUse"]["name"]) == "wait_60" :
                            st.write("\nProcessing result...\n")
                        elif str(content["toolUse"]["name"]) == "get_arxiv_list" :
                            st.write(f'\n**Research Assistant:** Doing an ArXiv Search on {content["toolUse"]["input"]["subject"]}')
                        elif str(content["toolUse"]["name"]) == "get_stock_info" :
                            st.write(f'\n**Research Assistant:** Retieving current stock information on {content["toolUse"]["input"]["ticker"]}')
                        elif str(content["toolUse"]["name"]) == "get_company_news" :
                            st.write(f'\n**Research Assistant:** Getting current financial news and company information {content["toolUse"]["input"]["ticker"]}')
                        else:
                            if (DEBUG) :
                                print("----------------TOOL CALL----------------------")
                                #print(str(kwargs))
                                print(str(content["toolUse"].get("name")))
                                print(str(content["toolUse"].get("input")))
                                print("------------------------------------")
                   
st.title("Deep Research Agent")   
streamable_http_mcp_client = MCPClient(create_streamable_http_transport)

# Use the MCP server in a context manager
with streamable_http_mcp_client:
    # Get the tools from the MCP server
    tools = streamable_http_mcp_client.list_tools_sync()
   
    if INTERNAL_SEARCH.lower() == "false" :
        sys_prompt = ("You are an experience research assistant.  When given a topic to reseach, you perform the following tasks in order: "
        "1. Generate " + NUM_QUESTIONS + " deep reaseach questions from the prompt "
        "2. Perform a web search on all the questions "
        "3. Perform an Arxiv search on the questions to find relevant acedemic information "
        "4. If any of the questions are regarding a company, find the stock ticker symbol for the company and get stock information for that ticker "
        "5. Perform a deep analysis on the relevant content to determine deep insights and trends "
        "6  Combine all the relevant information into a 1500 word report with the following format: "
        "   * Executive Summary - Summarize the deep analysis into a single paragraph that provides all the key information "
        "   * Details - Provide a 1 page response that supports the information in the executive summary "
        "   * Follow-up section - Provide any follow-up web links that support the information provided that the user can use to get more detailed if needed "
       )
    else:
        sys_prompt = ("You are an experience research assistant.  When given a topic to reseach, you perform the following tasks in order: "
        "1. Generate " + NUM_QUESTIONS + " deep reaseach questions from the prompt "
        "2. Perform a web search on all the questions "
        "3. Perform an Arxiv search on the questions to find relevant acedemic information "
        "4. If any of the questions are regarding a company, find the stock ticker symbol for the company and get stock information for that ticker "
        "5. Perform a deep analysis on the relevant content to determine deep insights and trends "
        "6. Performa an internal search on the prompt "
        "7  Combine all the relevant information into a 1500 word report with the following format: "
        "   * Executive Summary - Summarize the deep analysis into a single paragraph that provides all the key information "
        "   * Details - Provide a 1 page response that supports the information in the executive summary "
        "   * Follow-up section - Provide any follow-up web links that support the information provided that the user can use to get more detailed if needed "
        )

    # Create an agent with the MCP tools
    agent = Agent(model=model, tools=tools, callback_handler = my_callback_handler, system_prompt=sys_prompt)
   
    if query := st.chat_input("What would you like to research today?"):   
         
        if (query.lower() == "quit") :
            st.write("Goodbye!")
            exit()
        st.write(f"Topic: ** {query} **")       
            
        if (USE_GUARDRAILS.lower() == "true") and (apply_bedrock_guardrail(str(query), "INPUT") == "GUARDRAIL_INTERVENED"):
            #if it does, just abort and prompt for the next question
            #print("Guardrail intervened on the response:", guardrail_response["outputs"])
            st.write("I am sorry due to content restrictions, I cannot process this request")
        else:
            try:     
                response = agent(query)
            except Exception as e:
            
                print("ERROR CAUGHT")
                print("Error Identified - Backing off")
                print(e["error"])
                time.sleep(60)
                response = agent(query)
        
            if (USE_GUARDRAILS.lower() == "true") and (apply_bedrock_guardrail(str(response), "OUTPUT") == "GUARDRAIL_INTERVENED") :
            #if they do, just do not record the response and continue to research
                st.write("This topic has triggered a guardrail and may not contain a complete response")
                st.write("Report Complete - do you have another research topic?")  
            #print("Guardrail intervened on the response:", guardrail_response["outputs"])
            else:
                st.write("Report Complete - do you have another research topic?")               

    