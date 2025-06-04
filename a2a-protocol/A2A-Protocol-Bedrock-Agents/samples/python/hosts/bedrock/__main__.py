from common.server import A2AServer
from common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from common.utils.push_notification_auth import PushNotificationSenderAuth
from hosts.bedrock.task_manager import AgentTaskManager
from hosts.bedrock.agent import BedrockHostAgent
import click
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=30000)
def main(host, port):
    """Starts the Bedrock Inline Agent server."""
    try:

        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
        skill = AgentSkill(
            id="COORDINATE_AGENT_TASKS",
            name="host_agent",
            description="coordinate tasks between agents."
        )
        list_urls = [
        "http://localhost:60000/",
        "http://localhost:10000/",
        ]

        agent_card = AgentCard(
            name="host_agent",
            description="coordinate tasks between agents.",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=BedrockHostAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=BedrockHostAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        notification_sender_auth = PushNotificationSenderAuth()
        notification_sender_auth.generate_jwk()
        server = A2AServer(
            agent_card=agent_card,
            task_manager=AgentTaskManager(agent=BedrockHostAgent(remote_agent_addresses=list_urls), notification_sender_auth=notification_sender_auth),
            host=host,
            port=port,
        )

        server.app.add_route(
            "/.well-known/jwks.json", notification_sender_auth.handle_jwks_endpoint, methods=["GET"]
        )

        logger.info(f"Starting server on {host}:{port}")
        server.start()
    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()
