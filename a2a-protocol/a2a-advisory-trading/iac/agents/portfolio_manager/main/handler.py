import json
from datetime import datetime
from a2a_core import Task
from main import PortfolioManagerAgent
from a2a_core import get_logger

logger = get_logger({"agent": "PortfolioManagerHandler"})

def lambda_handler(event, context):
    body = None
    try:
        body = json.loads(event["body"])
        task = Task.from_dict(body.get("task"))
        input_data = task.input or {}

        agent = PortfolioManagerAgent()
        result = agent.analyze(input_data, task.id)
        print("Result of portfolio manager handler:", result)
        print("Check input of task:", task.input)
        task.output = result
        print("Check task output:", task.output)
        task.status = "completed"
        task.modified_at = datetime.now().isoformat()

        return {
            "statusCode": 200,
            "body": json.dumps(task.to_dict()),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logger.error("PortfolioManager handler failed", {
            "error": str(e),
            "event": event
        })

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

