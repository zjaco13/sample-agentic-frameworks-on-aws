import os
import boto3
import requests
from typing import Dict


def discover_agent_cards() -> Dict[str, str]:
    """
    Returns a dictionary mapping capability -> agent's send endpoint URL
    by discovering .well-known/agent.json for each registered API Gateway.
    """
    client = boto3.client("apigateway")
    region = os.environ.get("AWS_PRIMARY_REGION", "us-east-1")
    routing_table = {}

    response = client.get_rest_apis()

    for item in response["items"]:
        api_id = item["id"]
        name = item["name"]

        if not name.endswith("-api"):
            continue

        card_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/dev/.well-known/agent.json"

        try:
            r = requests.get(card_url, timeout=2)
            if r.status_code == 200:
                card = r.json()
                for capability in card.get("capabilities", []):
                    endpoint = card.get("endpoints", {}).get("send")
                    if endpoint:
                        routing_table[capability] = endpoint
        except Exception as e:
            print(f"Failed to fetch card from {card_url}: {e}")

    return routing_table
