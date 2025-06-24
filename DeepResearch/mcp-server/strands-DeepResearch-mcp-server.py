##File: strands-DeepResearch-mcp-server.py
#Author: Chris Smith
#Email: smithzgg@amazon.com
#Created: 06/15/2025
#Last Modified: 06/18/2025

#Description:
#    Deep Research MCP server with the following tools:
#       - Curent Weather reports
#       - Tavily Web tavily_web_search
#       - ArXviv Content Search
#       - ArXiv content Download and transform
#       - yFinance historical stock retreival
#       - yFinance Company info and current news search
#       

#Usage:
#    \$ python <filename>.py 
    
#Dependencies:
#   - Fastmcp
#   - arxiv Search library
#   - yFinance
#   - Tavily
#   - Markitdown for PDF to text conversion
#   - os and time for housekeeping and throttling

from mcp.server import FastMCP
from typing import Any
import httpx
import arxiv
import json
import time
import os
import yfinance as yf
from markitdown import MarkItDown
from tavily import TavilyClient
import boto3


# 0.0.0.0 configures the server to listten on all ports.  Change the IP and/or port number if needed.
mcp = FastMCP(host="0.0.0.0", port=8000, transport="streamable-http")
mydirpath = "/Users/smithzgg/papers/"
# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

guardrail_id = "<YOUR AWS Guardrail ID>"
guardrail_version = "<Your AWS Guardrail Version>"
knowledge_base_id = "<Your AWS KB ID>"

arxiv_client = arxiv.Client()
tavily_client = TavilyClient(api_key="<YOUR TAVILY API KEY>")
md = MarkItDown()

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


@mcp.tool(description="""Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """)
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool(description= """Get weather forecast for a location.
    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """ )
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool(description="Perform a search on an internal data source")
def search_internal(subject: str) -> str:
    bedrock_client = boto3.client('bedrock-agent-runtime', region_name="us-west-2")

    response = bedrock_client.retrieve(
        guardrailConfiguration={
            'guardrailId': guardrail_id,
            'guardrailVersion': guardrail_version
        },
        knowledgeBaseId=knowledge_base_id,
        retrievalQuery={
            'text': subject
        }
    )
    print(str(response))


@mcp.tool(description="Get a list of ArXiv papers related to a subject")
def get_arxiv_list(subject: str) -> str:
    # Search for the 10 most recent articles matching the keyword "quantum."
    search = arxiv.Search(
        query = subject,
        max_results = 3,
        sort_by = arxiv.SortCriterion.SubmittedDate
    )

    results = arxiv_client.results(search)
    data=[]
    # `results` is a generator; you can iterate over its elements one by one...
    for r in arxiv_client.results(search):
        print(r.title)
        data.append({"title" : r.title, "link": r.entry_id, "Summary" : r.summary})
    # ...or exhaust it into a list. Careful: this is slow for large results sets.
    all_results = list(results)
    #print(all_results)
    #print([r.title for r in all_results])
    time.sleep(30)
    return (json.dumps(data))

@mcp.tool(description="Get Contents of an ARXIV paper from the link")
def get_arxiv_content(link: str) -> str:
    paper_id = (link.split("/"))[-1]
    paper = next(arxiv.Client().results(arxiv.Search(id_list=[paper_id])))
    # Download the PDF to the PWD with a default filename.
    # paper.download_pdf()
    # Download the PDF to the PWD with a custom filename.
    #paper.download_pdf(filename="downloaded-paper.pdf")
    # Download the PDF to a specified directory with a custom filename.
    paper.download_pdf(dirpath=mydirpath, filename=paper_id + "'pdf")
    try:
        # Expand the tilde (if part of the path) to the home directory path
        #expanded_path = os.path.expanduser(file_path)
        # Use markitdown to convert the PDF to text
        return md.convert(mydirpath+paper_id+".pdf").text_content
    except Exception as e:
        # Return error message that the LLM can understand
        print( f"Error reading PDF: {str(e)}")
        return "Error Reading Content"
    
@mcp.tool(description="Perform a web Search on a question")
def tavily_web_search(question: str) -> str:
    gen_answer=tavily_client.search(question, search_depth="advanced", max_results = 1,
            topic="general", include_images=False, include_answer = "advanced")
    print("Searching General....")
    cur_answer=tavily_client.search(question, search_depth="advanced", max_results = 3,
            topic="news", include_images=False, days=30)
    print("Searching news....")
    print(question)
    print("Response is")
    answer = str(gen_answer) + " " + str(cur_answer)
    print(answer)
    time.sleep(15)
    return answer

@mcp.tool(description=""" get stock information for a company from its ticker symbol
    Args:
        ticker: str
        The ticker symbol of the stock to get historical data for, e.g. "IBM"
    """,
    )
async def get_stock_info(ticker: str ) -> str:
    """Get a stock information for a company from its ticker symbol
    Args:
        ticker: str
        The ticker symbol of the stock to get historical prices for, e.g. "IBM"
    """

    print("getting info for :" + ticker)
    try:
        company = yf.Ticker(ticker)
    except:
        print("Error geting company info")
        return "Error getting info - Retry"
    try:
        if company.isin is None:
            print(f"Company ticker {ticker} not found.")
            return f"Company ticker {ticker} not found."
    except Exception as e:
        print(f"Error: getting historical stock prices for {ticker}: {e}")
        return f"Error: getting historical stock prices for {ticker}: {e}"

    # If the company is found, get the historical data
    hist_data = company.history(period="1mo", interval="1d")
    hist_data = hist_data.reset_index(names="Date")
    hist_data = hist_data.to_json(orient="records", date_format="iso")
    print(hist_data)
    return hist_data

@mcp.tool(description=""" Get financial news for a company from its stock ticker
    Args:
        ticker: str
        The ticker symbol of the stock to get news for, e.g. "IBM"
    """,
    )
async def get_company_news(ticker: str ) -> str:
    """Get financial news for a company from its stock ticker
    Args:
        ticker: str
        The ticker symbol of the stock to get historical prices for, e.g. "IBM"
    """
    print("getting news for :" + ticker)
    try:
        company = yf.Ticker(ticker)
    except:
        print("error getting news")
        return "Error getting Information - Retry"
    try:
        if company.isin is None:
            print(f"Company ticker {ticker} not found.")
            return f"Company ticker {ticker} not found."
    except Exception as e:
        print(f"Error: getting historical stock prices for {ticker}: {e}")
        return f"Error: getting historical stock prices for {ticker}: {e}"

    # If the company is found, get the historical data
    info = str(company.info)
    news = str(company.news)
    report = info + news
    print(report)
    return report


@mcp.tool(description="wait 10 seconds")
def wait_10() :
    time.sleep(10)
    return

@mcp.tool(description="wait 60 seconds")
def wait_60() :
    time.sleep(60)
    return

mcp.run(transport="streamable-http")