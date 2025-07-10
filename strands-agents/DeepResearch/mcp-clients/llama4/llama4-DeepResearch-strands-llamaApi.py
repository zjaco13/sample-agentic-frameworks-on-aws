##File: llama4-DeepResearch-strands-llamaApi.py
#Author: Chris Smith
#Email: smithzgg@amazon.com
#Created: 06/15/2025
#Last Modified: 07/06/2025

#Description:
#    Deep Research MCP client using Llama4 built on the Strands
#    framework using the Llama API.  This example is shows the typical multi-turn
#    processing utilized for most Deep Research model orchestraion.  
#    It uses AWS guardrails to allow for custom restrictions
#    to the model behavoir if needed.

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
import os
import time

# set to 1 for verbose output
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

# Set your Llama API KEY.  Go to 
llama_api_key = os.getenv("LLAMA_API_KEY")


# Enables Strands debug log level
logging.getLogger("strands").setLevel(logging.ERROR)

#Replace with you LLama AP key
model = LlamaAPIModel(
    client_args={
      #  "api_key": "LLM|1438469257464983|Fpc81PXFEsZQfu_s3rvTo2GudDM",
        "api_key": llama_api_key,
    },
    # **model_config
    max_tokens=8192,
    model_id="Llama-4-Maverick-17B-128E-Instruct-FP8"
)

bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-west-2")

# Use this if you are running the MCP server on the same system, otherwise replace localhost 
# with the IP address of the MCP Server

def create_streamable_http_transport():
   return streamablehttp_client(mcp_server)

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

def guardrail_check(input: str) -> str:
     #check to ensure the model's response do not violate any of our guardrails
    guardrail_response = apply_bedrock_guardrail(input, "OUTPUT")
    #if they do, just do not record the response and continue to research
    if guardrail_response == "GUARDRAIL_INTERVENED":
            gr_response="This topic has triggered a guardrail and may not contain a complete response"
    else:
        gr_response=input
    return gr_response

def strands_turn(query: str, text: str) -> str:
    try:     
        response = agent(query)
    except Exception as e:
            
        print("ERROR CAUGHT")
        if e["type"] == "error":
            print("Error Identified - Backing off")
            print(e["error"])
        time.sleep(60)
        response = agent(query)
    if DEBUG:
        print("Response: " + str(response))
    #check to ensure the model's response do not violate any of our guardrails
        
    #check to ensure the model's response do not violate any of our guardrails
    if USE_GUARDRAILS.lower()=="true" :
        text=text + guardrail_check(str(response))
    else:
        text = text + str(response)
    return text

def my_callback_handler(**kwargs) :

    if "message" in kwargs and kwargs["message"].get("role") == "assistant" :
        for content in kwargs["message"]["content"] :
            if (USE_GUARDRAILS.lower() == "true") and (apply_bedrock_guardrail(str(content), "INPUT") == "GUARDRAIL_INTERVENED"):
                print("Uh-oh, this question has triggered my internal guardrails due to content restrictions, my answer may not include all the relevant data")
            else:
                if "text" in content:
                    #print("\n\n------------------------------------")                    #print(str(kwargs))
                    print(f'Research Assistant: {content["text"]}')
                    #print("------------------------------------\n")
               
                if "toolUse" in content :
                    if str(content["toolUse"]["name"]) == "tavily_web_search" :
                        print(f'\nResearch Assistant: Doing a web search on {content["toolUse"]["input"]["question"]}')
                    elif str(content["toolUse"]["name"]) == "wait_60" :
                        print("\nProcessing result...\n")
                    elif str(content["toolUse"]["name"]) == "get_arxiv_list" :
                        print(f'\nResearch Assistant: Doing an ArXiv Search on {content["toolUse"]["input"]["subject"]}')
                    elif str(content["toolUse"]["name"]) == "get_stock_info" :
                        print(f'\nResearch Assistant: Retieving current stock information on {content["toolUse"]["input"]["ticker"]}')
                    elif str(content["toolUse"]["name"]) == "get_company_news" :
                        print(f'\nResearch Assistant: Getting current financial news and company information {content["toolUse"]["input"]["ticker"]}')
                    else:
                        if (DEBUG) :
                            print("----------------TOOL CALL----------------------")
                            #print(str(kwargs))
                            print(str(content["toolUse"].get("name")))
                            print(str(content["toolUse"].get("input")))
                            print("------------------------------------")
   

#start MCP Client
streamable_http_mcp_client = MCPClient(create_streamable_http_transport)

with streamable_http_mcp_client:
    #Get Tool List from MCP Server
    tools = streamable_http_mcp_client.list_tools_sync()
    #Initialize STrands Agent
    #callback_handler = None for silent mode
     #callback_handler = None for silent mode
    if (DEBUG) :
        agent = Agent(model=model, tools=tools, system_prompt="You are a deep research assistant.") 
    else:   
        agent = Agent(model=model, tools=tools, callback_handler=my_callback_handler, system_prompt="You are a deep research assistant.")

    #User input loop
    while True:
        #get User Input
        query = input("\nQuery: ").strip()
        # type 'quit' to exit loop gracefully
        if query.lower() == 'quit':
            break
        # Step 1 - Generate 3 good deep research questions from the prompt        
        question_prompt = "Generate " + NUM_QUESTIONS + " deep research questions from the following prompt separate each question with the | symbol. Responds with only the questions." + query
        #Check to ensure the user prompt does not violate our internal rules
        if USE_GUARDRAILS.lower() == "true" :
            guardrail_response = apply_bedrock_guardrail(str(question_prompt), "INPUT")
        #if it does, just abort and prompt for the next question
        if USE_GUARDRAILS.lower() == "true" and guardrail_response == "GUARDRAIL_INTERVENED":
            print("I am sorry due to content restrictions, I cannot process this request")
        else:
            # Start Research
            try:     
                response1 = agent(question_prompt)
            except Exception as e:
            
                print("ERROR CAUGHT")
                print(e)
                time.sleep(60)
                response1 = agent(question_prompt)
            #questions_str = str(response1)
            questions_list = str(response1).split("|")
            #questions_list = questions_str.split("|")

            #format final context
            full_text = "<CONTENT>"
            #lets do a web search on each question
            # separately and collate the responses
            for question in questions_list :
                full_text = strands_turn("Perform a web search for the following question perform a detailed analysis with supporing links on the results:" + question, full_text)
                time.sleep(30)
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
            
            full_text=full_text + "</CONTENT>"

            fquery="From [CONTENT] generate a plan to write a detailed 1500 word report on this topic: " + query
        
            try:     
                plan = agent(fquery)
            except Exception as e:
            
                print("ERROR CAUGHT")
                if e["type"] == "error":
                    print("Error Identified - Backing off")
                    print(e["error"])
                time.sleep(60)
                plan = agent(fquery)

            plan = "<PLAN>" + str(plan) + "</PLAN>"
            final_query = "Execute this [PLAN] to generate a 1500 word report with the following sections 1/ Executive Summary 2/ Detailed Analysis, 3 /Supporting data, and 4/ Reference links on this [SUBJECT]: <SUBJECT>" + query + "</SUBJECT> \n include [CONTENT].  \n" + plan + "\n \n" + full_text
            if (DEBUG) :
                print("-----------------------------------")
                print(final_query)
                print("-----------------------------------")

            try:     
                final_report = agent(final_query)
            except Exception as e:
                print("ERROR CAUGHT")
                if e["type"] == "error":
                    print("Error Identified - Backing off")
                    print(e["error"])
                time.sleep(60)
                final_report = agent(final_query)

            print("Report Complete - Do you have another research topic?")
        