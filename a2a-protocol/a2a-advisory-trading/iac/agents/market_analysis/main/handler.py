import json
import uuid
from datetime import datetime
from a2a.types import Task, Message, Artifact, TaskStatus, TaskState
from main import MarketAnalysisAgent

agent = MarketAnalysisAgent()

def lambda_handler(event, context):
    # Support both Lambda proxy and direct call; unwrap A2A envelope if present
    try:
        if "body" in event and isinstance(event["body"], str):
            event_body = json.loads(event["body"])
        else:
            event_body = event

        # If this is a direct Lambda call via API Gateway HTTP API, unwrap A2A RPC
        if "method" in event_body and "params" in event_body and "message" in event_body["params"]:
            # Standard A2A envelope
            task_dict = event_body["params"]["message"]
            request_id = event_body.get("id") or str(uuid.uuid4())
        elif "task" in event_body:
            # Legacy direct invocation
            task_dict = event_body["task"]
            request_id = event_body.get("id") or str(uuid.uuid4())
        else:
            # Direct raw Task dict
            task_dict = event_body
            request_id = event_body.get("id") or str(uuid.uuid4())

        task = Task.model_validate(task_dict)
        result_task = agent.analyze(task)

        # Return as JSON-RPC envelope
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
            description="Error encountered during market analysis"
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
