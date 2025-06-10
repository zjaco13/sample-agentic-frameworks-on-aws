import json
import asyncio
import uuid
from datetime import datetime
from a2a.types import Task, Message, Artifact, TaskStatus, TaskState
from main import PortfolioManagerAgent
from a2a_core import get_logger

logger = get_logger({"agent": "PortfolioManagerHandler"})

def to_jsonable(obj):
    """
    Recursively convert all Pydantic objects in nested dict/list to dicts for JSON serialization.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode='json')
    elif isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_jsonable(i) for i in obj]
    else:
        return obj

def lambda_handler(event, context):
    return asyncio.get_event_loop().run_until_complete(_async_handler(event, context))

async def _async_handler(event, context):
    analyze_input = None
    request_id = None
    try:
        # === Step 1: Parse event body (unwrap Lambda or API Gateway structure) ===
        if isinstance(event, dict) and "body" in event:
            if isinstance(event["body"], str):
                body = json.loads(event["body"])
            else:
                body = event["body"]
        else:
            body = event

        # === Step 2: Unwrap A2A JSON-RPC envelope, if present ===
        if isinstance(body, dict) and "method" in body and "params" in body and "message" in body["params"]:
            # Standard A2A envelope (preferred for A2A)
            request_id = body.get("id") or str(uuid.uuid4())
            analyze_input = body["params"]["message"]
        elif isinstance(body, dict) and "task" in body:
            # Some wrappers (legacy, tests) may wrap with {"task": ...}
            request_id = body.get("id") or str(uuid.uuid4())
            analyze_input = body["task"]
        else:
            # Legacy/Direct Lambda invocation (accepts {user_input} or {trade_confirmation_phase, ...})
            request_id = body.get("id") or str(uuid.uuid4())
            analyze_input = body

        # Defensive: ensure analyze_input is a dict
        if not isinstance(analyze_input, dict):
            raise ValueError("Input data could not be normalized to a dict.")

        agent = PortfolioManagerAgent()
        # Route the payload to analyze; analyze_input must be Dict[str, Any]
        result = await agent.analyze(
            analyze_input,
            analyze_input.get("session_id") or analyze_input.get("contextId")
        )

        # --- RECURSIVELY convert any pydantic objects to dicts before serializing
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "message": to_jsonable(result)
            }
        }

        return {
            "statusCode": 200,
            "body": json.dumps(response)
        }

    except Exception as e:
        try:
            # Use task id/context id if available for tracing
            task_id = (
                    (analyze_input.get("session_id") if analyze_input else None)
                    or (analyze_input.get("contextId") if analyze_input else None)
                    or str(uuid.uuid4())
            )
        except Exception:
            task_id = str(uuid.uuid4())

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
            contextId=task_id,
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
            description="Error encountered during portfolio analysis"
        )

        # Return the error in A2A JSON-RPC envelope, recursively json-ifiable
        error_task = Task(
            id=task_id,
            contextId=task_id,
            status=status,
            artifacts=[error_artifact],
            kind="task"
        )

        error_response = {
            "jsonrpc": "2.0",
            "id": request_id if request_id else str(uuid.uuid4()),
            "result": {
                "message": to_jsonable(error_task)
            }
        }

        return {
            "statusCode": 500,
            "body": json.dumps(error_response)
        }
