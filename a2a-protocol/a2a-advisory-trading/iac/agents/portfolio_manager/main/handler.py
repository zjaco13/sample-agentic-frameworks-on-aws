import json
import asyncio
from datetime import datetime
from a2a_core import Task, get_logger
from main import PortfolioManagerAgent

logger = get_logger({"agent": "PortfolioManagerHandler"})

def lambda_handler(event, context):
    return asyncio.get_event_loop().run_until_complete(_async_handler(event, context))

async def _async_handler(event, context):
    try:
        print("Received event", {"event": event})
        
        if isinstance(event, dict):
            if "body" in event:
                body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
            else:
                body = event

        print("Processed body", {"body": body})

        if not body.get("task"):
            logger.error("No task in body")
            raise ValueError("No task provided in the request body")

        task = Task.from_dict(body.get("task"))
        print("Created task object", {"task_id": task.id})

        agent = PortfolioManagerAgent()
        print("Starting analysis", {"task_id": task.id})
        
        result = await agent.analyze(task.input or {}, task.id)
        print("Analysis completed", {"task_id": task.id, "result_status": result.get("status")})

        # Check if we need confirmation (Phase 1 response)
        if result.get("status") == "pending":
            response = {
                "statusCode": 202,  # Accepted
                "body": json.dumps({
                    "status": "pending",
                    "analysis_results": result["analysis_results"],
                    "trade_details": result["trade_details"],
                    "session_id": result["session_id"],
                    "summary": result["summary"],
                    "delegated_tasks": result["delegated_tasks"]
                }),
                "headers": {"Content-Type": "application/json"}
            }
            print("Returning pending response", {
                "task_id": task.id,
                "status_code": response["statusCode"]
            })
            return response

        # Normal completion (Phase 1 non-trade or Phase 2 trade execution)
        task.output = result
        task.status = "completed"
        task.modified_at = datetime.now().isoformat()

        response = {
            "statusCode": 200,
            "body": json.dumps(task.to_dict()),
            "headers": {"Content-Type": "application/json"}
        }
        print("Returning successful response", {
            "task_id": task.id,
            "status_code": response["statusCode"]
        })
        return response

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON body", {
            "error": str(e),
            "event_body": event.get("body") if isinstance(event, dict) else event
        })
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Invalid JSON in request body",
                "details": str(e)
            }),
            "headers": {"Content-Type": "application/json"}
        }
    
    except ValueError as e:
        logger.error("Validation error", {"error": str(e)})
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Validation error",
                "details": str(e)
            }),
            "headers": {"Content-Type": "application/json"}
        }

    except Exception as e:
        logger.error("Unexpected error in handler", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "error_type": type(e).__name__,
                "details": str(e)
            }),
            "headers": {"Content-Type": "application/json"}
        }
