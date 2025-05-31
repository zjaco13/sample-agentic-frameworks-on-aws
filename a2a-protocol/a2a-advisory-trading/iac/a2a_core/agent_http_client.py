import aiohttp
from .a2a_task import Task


async def send_task(task: Task, url: str, timeout: int = 5, retries: int = 3) -> Task:
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        url,
                        json={"task": task.to_dict()},
                        timeout=timeout,
                        headers={"Content-Type": "application/json"}
                ) as resp:

                    if resp.status == 200:
                        response_data = await resp.json()
                        return Task.from_dict(response_data)
                    else:
                        raise RuntimeError(f"Agent returned {resp.status}: {await resp.text()}")

        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to send task to {task.id} at {url}: {e}")
