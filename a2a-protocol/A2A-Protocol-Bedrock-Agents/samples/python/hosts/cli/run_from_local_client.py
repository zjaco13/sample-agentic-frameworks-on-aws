
# echo_client.py
import asyncio
import logging
import traceback
from uuid import uuid4

# Assuming common types and client are importable
from common.client import A2AClient, card_resolver # card_resolver might be needed
from common.types import Message, TextPart, AgentCard # Import AgentCard if needed directly

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://localhost:30000/"

async def main():
    client = A2AClient(url=SERVER_URL)

    task_id = f"echo-task-{uuid4().hex}"
    session_id = f"session-{uuid4().hex}"
    user_text = input("Enter your query: ")  # Example user input

    user_message = Message(
        role="user",
        parts=[TextPart(text=user_text)]
    )

    send_params = {
        "id": task_id,
        "sessionId": session_id,
        "message": user_message.model_dump(),
    }

    try:
        logger.info(f"Sending task {task_id} to {SERVER_URL}...")
        response = await client.send_task(payload=send_params)

        if response.error:
            logger.error(f"Task {task_id} failed: {response.error.message} (Code: {response.error.code})")
        elif response.result:
            task_result = response.result
            logger.info(f"Task {task_id} completed with state: {task_result.status.state}")
            
            # Check for artifacts first (where the content usually is for completed tasks)
            if task_result.artifacts and len(task_result.artifacts) > 0:
                for artifact in task_result.artifacts:
                    if artifact.parts and len(artifact.parts) > 0:
                        for part in artifact.parts:
                            if part.type == 'text':
                                print(part.text)
            
            # If no artifacts or no text in artifacts, check status message
            elif task_result.status.message and task_result.status.message.parts:
                for part in task_result.status.message.parts:
                    if part.type == 'text':
                        print(part.text)
            else:
                logger.warning("No content found in response")


    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"An error occurred while communicating with the agent: {e}")

if __name__ == "__main__":
    asyncio.run(main())
