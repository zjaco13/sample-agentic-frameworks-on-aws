import json
import uuid
from datetime import datetime
from a2a.types import Task, Message, Artifact, TaskStatus, TaskState
from main import TradeExecutionAgent

agent = TradeExecutionAgent()

def lambda_handler(event, context):
    try:
        # === Unwrap Lambda event body ===
        if "body" in event and isinstance(event["body"], str):
            body = json.loads(event["body"])
        else:
            body = event

        # === Unwrap A2A JSON-RPC envelope if present ===
        if "method" in body and "params" in body and "message" in body["params"]:
            request_id = body.get("id") or str(uuid.uuid4())
            task_dict = body["params"]["message"]
        else:
            request_id = body.get("id") or str(uuid.uuid4())
            task_dict = body.get("task") if "task" in body else body

        task = Task.model_validate(task_dict)

        result_task = agent.analyze(task)

        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "message": result_task.model_dump(mode='json')
            }
        }

        return {
            "statusCode": 200,
            "body": json.dumps(response)
        }

    except Exception as e:
        try:
            task_id = task.id if 'task' in locals() else str(uuid.uuid4())
            context_id = getattr(task, "contextId", None) if 'task' in locals() else None
        except Exception:
            task_id = str(uuid.uuid4())
            context_id = None

        error_parts = [
            {
                "kind": "text",
                "text": str(e),
                "metadata": {}
            }
        ]

        error_message = Message(
            role="agent",
            parts=error_parts,
            messageId=str(uuid.uuid4()),
            kind="message",
            taskId=task_id,
            contextId=str(context_id),
        )

        status = TaskStatus(
            state=TaskState.failed,
            message=error_message,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

        error_artifact = Artifact(
            artifactId=str(uuid.uuid4()),
            parts=error_parts,
            name="Error",
            description="Error encountered during trade execution"
        )

        error_task = Task(
            id=task_id,
            contextId=str(context_id),
            status=status,
            artifacts=[error_artifact],
            kind="task"
        )

        response = {
            "jsonrpc": "2.0",
            "id": request_id if 'request_id' in locals() else str(uuid.uuid4()),
            "result": {
                "message": error_task.model_dump(mode='json')
            }
        }

        return {
            "statusCode": 500,
            "body": json.dumps(response)
        }
