import json
from datetime import datetime
from a2a_core import Task
from main import MarketAnalysisAgent
from a2a_core import get_logger

logger = get_logger({"agent": "MarketAnalysisHandler"})

def lambda_handler(event, context):
    body = None
    try:
        body = json.loads(event["body"])
        task = Task.from_dict(body.get("task"))

        agent = MarketAnalysisAgent()
        result = agent.analyze(task.input or {})
        print("Market Analysis result completed.")
        task.output = result
        task.status = "completed"
        task.modified_at = datetime.now().isoformat()

        return {
            "statusCode": 200,
            "body": json.dumps(task.to_dict()),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logger.error("Handler failed", {"error": str(e), "event": event})

        task_id = "unknown"
        if body and isinstance(body, dict):
            task_id = body.get("task", {}).get("id", "unknown")

        error_task = Task(
            id=task_id,
            status="failed",
            error={"message": str(e), "type": type(e).__name__},
            created_at=datetime.now().isoformat(),
            modified_at=datetime.now().isoformat()
        )

        return {
            "statusCode": 500,
            "body": json.dumps(error_task.to_dict()),
            "headers": {"Content-Type": "application/json"}
        }
