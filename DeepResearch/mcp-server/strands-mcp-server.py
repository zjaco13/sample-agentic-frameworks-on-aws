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

mcp = FastMCP("DeepResearch Server")

# enter a local directory where ArXiv content can be downloaded
mydirpath = "<local Download Directory>"
# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

#initialize Clients
arxiv_client = arxiv.Client()
tavily_client = TavilyClient(api_key="<Your TAVILY API Key HERE")
md = MarkItDown()

#Tool to get a detailed list of ArXiv paper on a particular subject
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
    time.sleep(30)
    return (json.dumps(data))

#Tool to download ArXiv PDF and convert to text 
# from the link provided from list.

@mcp.tool(description="Get Contents of an ARXIV paper from the link")
def get_arxiv_content(link: str) -> str:
    paper_id = (link.split("/"))[-1]
    paper = next(arxiv.Client().results(arxiv.Search(id_list=[paper_id])))
    # Download the PDF to the specified directory with a custom filename.
    paper.download_pdf(dirpath=mydirpath, filename=paper_id + "'pdf")
    try:
        # Use markitdown to convert the PDF to text
        return md.convert(mydirpath+paper_id+".pdf").text_content
    except Exception as e:
        # Return error message that the LLM can understand
        print( f"Error reading PDF: {str(e)}")
        return "Error Reading Content"

 # Use Tavily web search tool to perform deep search on a deep research question 
@mcp.tool(description="Perform a web Search on a question")
def tavily_web_search(question: str) -> str:
    answer=tavily_client.search(question, search_depth="advanced", max_results = 3,
            include_images=False, include_answer = "advanced")
    print("Searching....")
    print(question)
    print("Response is")
    print(answer)
    time.sleep(30)
    return answer

#Use Yahoo finance to get historical stock information for a company
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
    company = yf.Ticker(ticker)
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
    return hist_data

#use yahoo Finance to get current information and news about a company
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
    company = yf.Ticker(ticker)
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
    return report

#optional wait tool to throttle requests if needed.
@mcp.tool(description="wait 10 seconds")
def wait_10() :
    time.sleep(10)
    return

mcp.run(transport="streamable-http")