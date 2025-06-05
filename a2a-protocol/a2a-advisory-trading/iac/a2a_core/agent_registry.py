import os
import boto3
import aiohttp
import asyncio
from typing import Dict

LOCAL_AGENT_CARD_URLS = [
    "http://localhost:8000/.well-known/agent.json",
    "http://localhost:8001/.well-known/agent.json",
    "http://localhost:8002/.well-known/agent.json",
    "http://localhost:8003/.well-known/agent.json"
]

async def fetch_agent_card(session, url: str) -> Dict[str, str]:
    try:
        async with session.get(url, timeout=2) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Failed to fetch card from {url}: {e}")
    return {}

async def discover_agent_cards() -> Dict[str, str]:
    env = os.environ.get("ENV_NAME", "dev").lower()
    routing_table = {}

    async with aiohttp.ClientSession() as session:
        tasks = []
        if env == "dev":
            client = boto3.client("apigateway")
            region = os.environ.get("AWS_PRIMARY_REGION", "us-east-1")
            response = client.get_rest_apis()
            for item in response["items"]:
                api_id = item["id"]
                name = item["name"]
                if not name.endswith("-api"):
                    continue
                card_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/dev/.well-known/agent.json"
                tasks.append(fetch_agent_card(session, card_url))
        else:
            for url in LOCAL_AGENT_CARD_URLS:
                tasks.append(fetch_agent_card(session, url))

        results = await asyncio.gather(*tasks)
        for card in results:
            if card:
                for skill in card.get("skills", []):
                    endpoint = card.get("endpoints", {}).get("send")
                    if endpoint:
                        routing_table[skill] = endpoint
    return routing_table
