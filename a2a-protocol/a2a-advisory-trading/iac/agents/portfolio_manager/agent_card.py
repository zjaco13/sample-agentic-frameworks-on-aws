import json
import os

def lambda_handler(event, context):
    domain = event['requestContext']['domainName']
    model_id = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
    region = os.environ.get("AWS_REGION", "us-east-1")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "id": "portfolio-manager-agent",
            "name": "PortfolioManagerAgent",
            "description": "Autonomously orchestrates market, risk, and trade analysis based on user goals.",
            "protocol": "A2A/1.0",
            "skills": ["OrchestratePortfolioInsights"],
            "endpoints": {
                "send": f"https://{domain}/dev/tasks/send"
            },
            "metadata": {
                "streaming": True,
                "modelId": model_id,
                "region": region,
                "provider": "Bedrock/Anthropic",
                "agent_type": "orchestrator",
                "observability": {
                    "logs": True,
                    "traceability": True
                }
            }
        }),
        "headers": {
            "Content-Type": "application/json"
        }
    }
