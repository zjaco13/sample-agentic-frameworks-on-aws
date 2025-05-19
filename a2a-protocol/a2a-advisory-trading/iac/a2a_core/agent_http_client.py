import requests
from .a2a_task import Task

def send_task(task: Task, url: str, timeout: int = 5, retries: int = 3) -> Task:
    for attempt in range(retries):
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"task": task.to_dict()},
                timeout=timeout
            )

            if response.status_code == 200:
                return Task.from_dict(response.json())
            else:
                raise RuntimeError(f"Agent returned {response.status_code}: {response.text}")

        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to send task to {url}: {e}")
