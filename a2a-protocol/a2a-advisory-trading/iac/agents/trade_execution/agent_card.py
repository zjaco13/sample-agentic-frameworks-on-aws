import json
import os

def lambda_handler(event, context):
    domain = event['requestContext']['domainName']
    region = os.environ.get("AWS_REGION", "us-east-1")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "id": "trade-execution-agent",
            "name": "TradeExecutionAgent",
            "description": "Executes trades and logs them to DynamoDB.",
            "protocol": "A2A/1.0",
            "skills": ["ExecuteTrade"],
            "endpoints": {
                "send": f"https://{domain}/dev/tasks/send"
            },
            "metadata": {
                "writesTo": "DynamoDB",
                "table": os.environ.get("TRADE_LOG_TABLE", "TradeExecutionLog"),
                "region": region
            }
        }),
        "headers": {
            "Content-Type": "application/json"
        }
    }
