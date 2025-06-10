import aiohttp
import json
import uuid
from a2a.types import Task

async def send_task(task: Task, endpoint: str, skill: str, timeout: int = 30) -> Task:
    """
    Sends a Task to a remote agent using A2A-compliant JSON-RPC via /message/send.
    Accepts both raw Task response and JSON-RPC wrapped result.message.
    """
    try:
        request_id = task.id or str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/send",
            "params": {
                "skill": skill,
                "message": task.model_dump(mode='json')
            }
        }

        print(f"=== Sending A2A task to {skill} ===")
        print(f"Endpoint: {endpoint}")
        print("Payload:", json.dumps(payload, indent=2)[:500])

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=timeout
            ) as response:
                response_text = await response.text()
                print(f"=== Response from {skill} ===")
                print(f"Status code: {response.status}")
                print(f"Response body: {response_text[:500]}")

                if response.status != 200:
                    raise RuntimeError(f"Agent returned {response.status}: {response_text}")

                # Accept both agent raw Task and JSON-RPC 'result.message'
                try:
                    response_data = await response.json()
                except Exception:
                    response_data = json.loads(response_text)

                if isinstance(response_data, dict) and "result" in response_data:
                    # Official A2A JSON-RPC
                    task_json = response_data["result"].get("message")
                else:
                    # Raw Task (legacy, current FastAPI style)
                    task_json = response_data

                if not task_json:
                    raise RuntimeError(f"Missing Task in agent reply: {response_data}")

                response_task = Task.model_validate(task_json)
                return response_task

    except Exception as e:
        print(f"Error sending task to {skill} at {endpoint}: {e}")
        raise
