import os
import boto3
import aiohttp
import asyncio
from typing import Dict


async def fetch_agent_card(session, url: str) -> Dict[str, str]:
    try:
        async with session.get(url, timeout=2) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Failed to fetch card from {url}: {e}")
    return {}


async def discover_agent_cards() -> Dict[str, str]:
    client = boto3.client("apigateway")
    region = os.environ.get("AWS_PRIMARY_REGION", "us-east-1")
    routing_table = {}

    response = client.get_rest_apis()
    tasks = []

    async with aiohttp.ClientSession() as session:
        for item in response["items"]:
            api_id = item["id"]
            name = item["name"]

            if not name.endswith("-api"):
                continue

            card_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/dev/.well-known/agent.json"
            tasks.append(fetch_agent_card(session, card_url))

        results = await asyncio.gather(*tasks)

        for card in results:
            if card:
                for capability in card.get("capabilities", []):
                    endpoint = card.get("endpoints", {}).get("send")
                    if endpoint:
                        routing_table[capability] = endpoint

    return routing_table



