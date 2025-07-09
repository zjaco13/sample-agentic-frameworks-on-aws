##File: Mistral-DeepResearch-strands-Bedrock.py
#Author: Chris Smith
#Email: smithzgg@amazon.com
#Created: 06/15/2025
#Last Modified: 06/18/2025

#Description:
#    Deep Research MCP client using Pixtral Large 2502 built on the Strands
#    framework using the AWS Bedrock API.  This example is shows the typical multi-turn
#    processing utilized for most Deep Research model orchestraion.  
#    It uses AWS guardrails to allow for custom restrictions
#    to the model behavoir if needed.

#Usage:
#    \$ python <filename>.py 
    
#Dependencies:
#    - mcp
#    - strands
#    - boto3


from mcp.client.streamable_http import streamablehttp_client
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
import logging
import boto3
import time

DEBUG = 0
#set this variable to the number of deep research questions you want to generate for the research topic
#more questions = more depth, but more processing time and context
#default is 3
NUM_QUESTIONS = "3"
#set to true if you want to include searching internal AWS Knowledge Bases
INTERNAL_SEARCH = "false"
#set to true if you want to use custom AWS Guardrails
USE_GUARDRAILS = "false"

# Replace with your actual guardrail ID and version
guardrail_id = "k4k67kbtf8eh"
guardrail_version = "2"
#bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-west-2")


# Enables Strands debug log level
logging.getLogger("strands").setLevel(logging.ERROR)

# Sets the logging format and streams logs to stderr
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

if USE_GUARDRAILS.lower() == "true" :
    model = BedrockModel(
     # **model_config
        max_tokens=16384,
        model_id="us.mistral.pixtral-large-2502-v1:0",
        streaming=False,
        guardrail_id=guardrail_id,       
        guardrail_version=guardrail_version,           
        #guardrail_trace="enabled"               # Enable trace info for debugging
    )
else:
    model = BedrockModel(
     # **model_config
        max_tokens=16384,
        model_id="us.mistral.pixtral-large-2502-v1:0",
        streaming=False
    )

# Call Strands agent and check for guardrails if needed.

def strands_turn(query: str, text: str) -> str:
   
    if DEBUG :
        print(query)
    response = agent(query)
    if response.stop_reason == "guardrail_intervened":
        print("Content was blocked by guardrails, conversation context overwritten!")
        text = text + "This topic has triggered a guardrail and may not contain a complete response"
    else:
        text = text + str(response)
    time.sleep(60)
    return text

# Use this if you are running the MCP server on the same system, otherwise replace localhost 
# with the IP address of the MCP Server

def create_streamable_http_transport():
   return streamablehttp_client("http://localhost:8000/mcp/")

streamable_http_mcp_client = MCPClient(create_streamable_http_transport)

# Use the MCP server in a context manager
with streamable_http_mcp_client:
    #Get Tool List from MCP Server
    tools = streamable_http_mcp_client.list_tools_sync()
    #Initialize STrands Agent
    #callback_handler = None for silent mode
    if (DEBUG) :
        agent = Agent(model=model, tools=tools, system_prompt="You are a deep research assistant.") 
    else:   
        agent = Agent(model=model, tools=tools, callback_handler=None, system_prompt="You are a deep research assistant.")

    #User input loop
    while True:
        #get User Input
        query = input("\nQuery: ").strip()
        # type 'quit' to exit loop gracefully
        if query.lower() == 'quit':
            break
        # Step 1 - Generate 3 good deep research questions from the prompt        
        question_prompt = "Generate " + NUM_QUESTIONS + " deep research questions from the following prompt. Please separate each question with the | symbol.  Respond with only the questions:" + query
        if (DEBUG):
            print(question_prompt)
        # Start Research
        response1 = agent(question_prompt)
        if DEBUG:
            print(response1)
        if response1.stop_reason == "guardrail_intervened":
            print("Content was blocked by guardrails, conversation context overwritten!")
        else:
            questions_str = str(response1)
            questions_list = questions_str.split("|")
            #format final context
            full_text = "<CONTENT>"

            #lets do a web search on each question
            # separately and collate the responses
            for question in questions_list :
                full_text = strands_turn("Perform a web search for the following question perform a detailed analysis with supporing links on the results:" + question, full_text)
            
            # For Deep research, we should also search ArXiv to see what recent papers have been published on
            # this topic
            full_text = strands_turn("Perform an arXiv search on the following subject: " + query, full_text)
            
            #lets also check the historical stock performance if applicable
            full_text = strands_turn("If the following prompt contains a company name, find the stock ticker for that company and get stock info for it: " + query, full_text)
               
            #finally we can get detailed company information and recent news 
            full_text = strands_turn("If the following prompt contains a company name, find the stock ticker for that company and get financial news for it: " + query, full_text)
         
             # Lets make sure to search our internal data sources also
            if INTERNAL_SEARCH.lower() == "true" : 
                full_text = strands_turn("Search internal data sources for information on " + query, full_text)
            
            full_text=full_text + "</CONTENT>"

            #We take all the collated information and analzye, summarize and format a final report.
            #This section can be modified to create any desired report format
            fquery="From [CONTENT] generate a plan to write a detailed 1500 word report on this topic: " + query
            plan = agent(fquery)
            plan = "<PLAN>" + str(plan) + "</PLAN>"
            final_query = "Execute this [PLAN] to generate a 1500 word report with the following sections 1/ Executive Summary 2/ Detailed Analysis, 3 /Supporting data, and 4/ Reference links on this [SUBJECT]: <SUBJECT>" + query + "</SUBJECT> \n include [CONTENT].  \n" + plan + "\n \n" + full_text
            if (DEBUG) :
                print("-----------------------------------")
                print(final_query)
                print("-----------------------------------")
          

            final_report = agent(final_query)
            if USE_GUARDRAILS.lower() == "true" :
                print(guardrail_check(str(final_report)))
            else:
                print(str(final_report))
        


            