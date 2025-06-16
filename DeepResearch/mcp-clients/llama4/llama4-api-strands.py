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

# Replace with your actual guardrail ID and version
guardrail_id = "k4k67kbtf8eh"
guardrail_version = "2"
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-west-2")

# Enables Strands debug log level
logging.getLogger("strands").setLevel(logging.ERROR)

#Replace with you LLama AP key
model = LlamaAPIModel(
    client_args={
        "api_key": "LLM|1438469257464983|Fpc81PXFEsZQfu_s3rvTo2GudDM",
    },
    # **model_config
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
        guardrail_response = apply_bedrock_guardrail(str(question_prompt), "INPUT")
        #if it does, just abort and prompt for the next question
        if guardrail_response["action"] == "GUARDRAIL_INTERVENED":
            print("Guardrail intervened on the response:", guardrail_response["outputs"])
            print("I am sorry due to content restrictions, I cannot process this request")
        else:
            # Start Research
            response1 = agent(question_prompt)
            questions_str = str(response1)
            questions_list = questions_str.split("|")

            #format final context
            full_text = "[Content]"
            #lets do a web search on each question
            # separately and collate the responses
            for question in questions_list :
                qquery = "Perform a web search for the following question:" + question
                response = agent(qquery)
                #check to ensure the model's response do not violate any of our guardrails
                guardrail_response = apply_bedrock_guardrail(str(response), "OUTPUT")
                #if they do, just do not record the response and continue to research
                if guardrail_response["action"] == "GUARDRAIL_INTERVENED":
                    full_text = full_text + "This topic has triggered a guardrail and may not contain a complete response"
                    print("Guardrail intervened on the response:", guardrail_response["outputs"])
                else:
                    full_text = full_text + str(response)
            # For Deep research, we should also search ArXiv to see what recent papers have been published on
            # this topic
            xquery="Perform an arXiv search on the following subject: " + query
            response = agent(xquery)
            guardrail_response = apply_bedrock_guardrail(str(response), "OUTPUT")
            if guardrail_response["action"] == "GUARDRAIL_INTERVENED":
                full_text = full_text + "This topic has triggered a guardrail and may not contain a complete response"
                print("Guardrail intervened on the response:", guardrail_response["outputs"])
            else:
                full_text = full_text + str(response)

            #lets also check the historical stock performance if applicable
            squery="If the following prompt contains a company name, find the stock ticker for that company and get stock info for it: " + query
            response = agent(squery)
            guardrail_response = apply_bedrock_guardrail(str(response), "OUTPUT")
            if guardrail_response["action"] == "GUARDRAIL_INTERVENED":
                full_text = full_text + "This topic has triggered a guardrail and may not contain a complete response"
                print("Guardrail intervened on the response:", guardrail_response["outputs"])
            else:
                full_text = full_text + str(response)

            #finally we can get detailed company information and recent news 
            snquery="If the following prompt contains a company name, find the stock ticker for that company and get financial news for it: " + query
            response = agent(snquery)
            guardrail_response = apply_bedrock_guardrail(str(response), "OUTPUT")
            if guardrail_response["action"] == "GUARDRAIL_INTERVENED":
                full_text = full_text + "This topic has triggered a guardrail and may not contain a complete response"
                print("Guardrail intervened on the response:", guardrail_response["outputs"])
            else:
                full_text = full_text + str(response)

            full_text=full_text + "[Content]"

            #We take all the collated information and analzye, summarize and format a final report.
            #This section can be modified to create any desired report format
            
            query ="You must do the following things: \
                1/ Perform a deep analysis on the following <Content> \
                2/ Summarize the results  \
                3/ Generate a detailed one page report \
                that includes an Executive Summary,  \
                Supporting Details, and specific references and  \
                links to support the findings." + full_text

            response = agent(query)
            guardrail_response = apply_bedrock_guardrail(str(response), "OUTPUT")

            if guardrail_response["action"] == "GUARDRAIL_INTERVENED":
                print("I am sorry, but I am not authorized to research this question", guardrail_response["outputs"])
            else:
                print(response)