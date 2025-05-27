from datetime import datetime
import json
import logging
from a2a_core import Task
from main import RiskAssessmentAgent

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        print("Risk assessment request received", {"event": event})
        body = json.loads(event.get("body", "{}"))
        task = Task.from_dict(body.get("task"))

        if not task.input:
            raise ValueError("Missing input data in task")

        analysis_type = task.input.get("analysisType", "general")

        if analysis_type == "asset":
            specific_asset = task.input.get("specificAsset", {})
            if not specific_asset:
                raise ValueError("Missing specificAsset data for asset analysis")
            if not all(k in specific_asset for k in ["symbol", "quantity"]):
                raise ValueError("Missing required fields in specificAsset")

        elif analysis_type == "sector":
            if not task.input.get("sector"):
                raise ValueError("Missing sector for sector analysis")

        agent = RiskAssessmentAgent()

        risk_analysis = agent.analyze(task.input or {})

        task.output = risk_analysis
        task.status = "completed"
        task.modified_at = datetime.utcnow().isoformat()

        print("Risk assessment complete", {
            "task_id": task.id,
            "analysis_type": analysis_type,
            "rating": risk_analysis.get("rating")
        })

        return {
            "statusCode": 200,
            "body": json.dumps(task.to_dict()),  # Changed from task.json() to task.to_dict()
            "headers": {
                "Content-Type": "application/json"
            }
        }

    except ValueError as ve:
        error_message = str(ve)
        logger.error("Validation error", {"error": error_message})
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": error_message,
                "status": "failed"
            }),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        error_message = str(e)
        logger.error("Risk assessment failed", {"error": error_message})
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": error_message,
                "status": "failed"
            }),
            "headers": {"Content-Type": "application/json"}
        }
