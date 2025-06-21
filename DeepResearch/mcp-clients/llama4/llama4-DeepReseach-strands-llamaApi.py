##File: llama4-DeepResearch-strands-llamaApi.py
#Author: Chris Smith
#Email: smithzgg@amazon.com
#Created: 06/15/2025
#Last Modified: 06/18/2025

#Description:
#    Deep Research MCP client using Llama4 built on the Strands
#    framework using the Llama API.  This example is shows the typical multi-turn
#    processing utilized for most Deep Research model orchestraion.  
#    It uses AWS guardrails to allow for custom restrictions
#    to the model behavoir if needed. It also implements the ability to 
#    search an internal AWS Knowledge base and incorporate the results into
#    the final report.

#Usage:
#    \$ python <filename>.py 
    
#Dependencies:
#    - mcp
#    - strands
#    - boto3

from strands import Agent,tool
from strands.models.llamaapi import LlamaAPIModel
from strands_tools import calculator
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
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
guardrail_id = "<Your Guardrail ID>"
guardrail_version = "<Your Guardrail version>"
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-west-2")

# Enables Strands debug log level
logging.getLogger("strands").setLevel(logging.ERROR)

#Replace with you LLama AP key
model = LlamaAPIModel(
    client_args={
        "api_key": "<Your Llama API Key>",
    },
    # **model_config
    max_tokens=8196,
    model_id="Llama-4-Maverick-17B-128E-Instruct-FP8"
)

# Use this if you are running the MCP server on the same system, otherwise replace localhost 
# with the IP address of the MCP Server

def create_streamable_http_transport():
   return streamablehttp_client("http://localhost:8000/mcp/")

# function to apply Bedrock Guardrails.  
# Insert any custom Python code for additional guardrails

def apply_bedrock_guardrail(input_text, source):
    
    gr_response = bedrock_runtime.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=guardrail_version,
        source=source,  
        content=[{"text": {"text": input_text}}]
    )
    return gr_response

def guardrail_check(input: str) -> str:
     #check to ensure the model's response do not violate any of our guardrails
    guardrail_response = apply_bedrock_guardrail(input, "OUTPUT")
    #if they do, just do not record the response and continue to research
    if guardrail_response["action"] == "GUARDRAIL_INTERVENED":
            gr_response="This topic has triggered a guardrail and may not contain a complete response"
            print("Guardrail intervened on the response:", guardrail_response["outputs"])
    else:
        gr_response=input
    return gr_response

def strands_turn(query: str, text: str) -> str:
    response = agent(query)
    #check to ensure the model's response do not violate any of our guardrails
    if USE_GUARDRAILS.lower()=="true" :
        text=text + guardrail_check(str(response))
    else:
        text = text + str(response)
    return text

#start MCP Client
streamable_http_mcp_client = MCPClient(create_streamable_http_transport)
with streamable_http_mcp_client:
    #Get Tool List from MCP Server
    tools = streamable_http_mcp_client.list_tools_sync()
    #Initialize STrands Agent
    #callback_handler = None for silent mode
    agent = Agent(model=model, tools=tools, callback_handler=None, system_prompt="You are a deep research assistant")

    #User input loop
    while True:
        #get User Input
        query = input("\nQuery: ").strip()
        # type 'quit' to exit loop gracefully
        if query.lower() == 'quit':
            break
        # Step 1 - Generate 3 good deep research questions from the prompt        
        question_prompt = "Generate " + NUM_QUESTIONS + " deep research questions from the following prompt separate each question with the | symbol:" + query
        #Check to ensure the user prompt does not violate our internal rules
        if USE_GUARDRAILS.lower() == "true" :
            guardrail_response = apply_bedrock_guardrail(str(question_prompt), "INPUT")
        #if it does, just abort and prompt for the next question
        if USE_GUARDRAILS.lower() == "true" and guardrail_response["action"] == "GUARDRAIL_INTERVENED":
            print("Guardrail intervened on the response:", guardrail_response["outputs"])
            print("I am sorry due to content restrictions, I cannot process this request")
        else:
            # Start Research
            response1 = agent(question_prompt)
            questions_list = str(response1).split("|")
            #questions_list = questions_str.split("|")

            #format final context
            full_text = "[Content]"
            #lets do a web search on each question
            # separately and collate the responses
            for question in questions_list :
                full_text = strands_turn("Perform a web search for the following question:" + question, full_text)
               
            # For Deep research, we should also search ArXiv to see what recent papers have been published on
            # this topic
            full_text = strands_turn("Perform an arXiv search on the following subject: " + query, full_text)
            

            #lets also check the historical stock performance if applicable
            full_text = strands_turn("If the following prompt contains a company name, find the stock ticker for that company and get stock info for it: " + query, full_text)
            

            #we can get detailed company information and recent news 
            full_text = strands_turn("If the following prompt contains a company name, find the stock ticker for that company and get financial news for it: " + query, full_text)
            

              # Lets make sure to search our internal data sources also
            if INTERNAL_SEARCH.lower() == "true" : 
                full_text = strands_turn("Search internal data sources for information on " + query, full_text)
            

            full_text=full_text + "[Content]"

            query="From <Content> generate a plan to write a detailed 1500 word report on this topic: " + full_text
            plan = agent(query)
            plan = "<plan>" + str(plan) + "</plan>"
            final_query = "Execute this [plan] to generate a 1500 word report with the following sections 1/Executive Summary 2/Detailed Analysis, Supporting data, and 3/ Reference links to answer this question: " + query + " \n" + plan + "\n include this [Content] + \n" + full_text
            
            final_report = agent(final_query)
            if USE_GUARDRAILS.lower() == "true" :
                print(guardrail_check(str(final_report)))
            else:
                print(str(final_report))
        