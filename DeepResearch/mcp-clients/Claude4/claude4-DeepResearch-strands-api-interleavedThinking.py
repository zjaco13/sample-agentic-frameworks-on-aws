
#File: claude4-DeepResearch-strands-api-interleavedThinking.py
#Author: Chris Smith
#Email: smithzgg@amazon.com
#Created: 06/15/2025
#Last Modified: 06/18/2025

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
#    - strands
#    - boto3

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent, tool
from strands.models.anthropic import AnthropicModel
from strands.tools.mcp.mcp_client import MCPClient
import logging
import boto3

#set this variable to the number of deep research questions you want to generate for the research topic
#more questions = more depth, but more processing time and context
#default is 3
NUM_QUESTIONS = "3"
#set to true if you want to include searching internal AWS Knowledge Bases
INTERNAL_SEARCH = "false"
#set to true if you want to use custom AWS Guardrails
USE_GUARDRAILS = "false"


# Replace with your actual guardrail ID and version
guardrail_id = "<Your Guardrail ID here>"
guardrail_version = "<Your Guardrail Version here>"
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
        "api_key": "<Your Anthropic API Key here>",
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
   return streamablehttp_client("http://localhost:8000/mcp/")
   #return streamablehttp_client("http://54.245.166.249:8000/mcp/")
   

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
        "IMPORTANT: Always wait 60 seconds between tool calls")
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
        "IMPORTANT: Always wait 60 seconds between tool calls")


    # Create an agent with the MCP tools
    agent = Agent(model=model, tools=tools, callback_handler = None, system_prompt=sys_prompt)
    while True:
        try:
            query = input("\nQuery: ").strip()
                
            if query.lower() == 'quit':
                break
            if (USE_GUARDRAILS.lower() == "true") and (apply_bedrock_guardrail(str(query), "INPUT") == "GUARDRAIL_INTERVENED"):
                #if it does, just abort and prompt for the next question
                #print("Guardrail intervened on the response:", guardrail_response["outputs"])
                print("I am sorry due to content restrictions, I cannot process this request")
            else:
                response = agent(query)
        
                if (USE_GUARDRAILS.lower() == "true") and (apply_bedrock_guardrail(str(response), "OUTPUT") == "GUARDRAIL_INTERVENED") :
                    #if they do, just do not record the response and continue to research
                    print("This topic has triggered a guardrail and may not contain a complete response")
                    #print("Guardrail intervened on the response:", guardrail_response["outputs"])
                else:
                    print("\n" + str(response))                 
        except Exception as e:
            print(f"\nError: {str(e)}")

    