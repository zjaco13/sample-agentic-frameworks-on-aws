import json
import os

def lambda_handler(event, context):
    domain = event['requestContext']['domainName']
    region = os.environ.get("AWS_REGION", "us-east-1")
    model_id = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "id": "risk-assessment-agent",
            "name": "RiskAssessmentAgent",
            "description": "Provides risk evaluations for trade decisions using Bedrock.",
            "protocol": "A2A/1.0",
            "skills": ["RiskEvaluation"],
            "endpoints": {
                "send": f"https://{domain}/dev/tasks/send"
            },
            "metadata": {
                "streaming": True,
                "modelId": model_id,
                "region": region,
                "provider": "Bedrock/Anthropic"
            }
        }),
        "headers": {
            "Content-Type": "application/json"
        }
    }
