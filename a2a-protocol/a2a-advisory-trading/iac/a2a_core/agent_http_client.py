from .a2a_task import Task
import aiohttp
import json
import logging

logger = logging.getLogger(__name__)

async def send_task(task: Task, endpoint: str, skill: str, timeout: int = 30) -> Task:
    try:
        print(f"=== Sending task to {skill} ===")
        print(f"Endpoint: {endpoint}")
        print(f"Task payload: {json.dumps(task.to_dict(), indent=2)}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                json={"task": task.to_dict()},
                headers={"Content-Type": "application/json"},
                timeout=timeout
            ) as response:
                print(f"=== Response from {skill} ===")
                print(f"Status code: {response.status}")

                response_text = await response.text()
                print(f"Response body: {response_text[:500]}")

                if response.status != 200:
                    raise RuntimeError(f"Agent returned {response.status}: {response_text}")

                response_data = await response.json()
                response_task = Task.from_dict(response_data)

                print(f"=== Processed response for {skill} ===")
                print(f"Response task status: {response_task.status}")
                print(f"Response task output: {json.dumps(response_task.output, indent=2)}")

                return response_task

    except aiohttp.ClientError as e:
        logger.error(f"Connection failed to {skill}", {
            "endpoint": endpoint,
            "error": str(e)
        })
        raise

    except Exception as e:
        logger.error(f"Failed to send task to {skill}", {
            "endpoint": endpoint,
            "error": str(e)
        })
        raise

