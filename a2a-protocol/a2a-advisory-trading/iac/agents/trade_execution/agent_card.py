import os
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentProvider

def lambda_handler(event, context):
    domain = event['requestContext']['domainName']
    env = event['requestContext'].get('env', 'dev')

    skill = AgentSkill(
        id="trade-execution",
        name="Trade Execution",
        description=(
            "Handles order placement and trade monitoring. "
        ),
        tags=["finance", "trading", "execution", "orders", "aws"],
        examples=[
            "Execute a market order to buy 100 shares of TSLA",
            "Place a limit order to sell 50 shares of AAPL",
        ],
        inputModes=["text"],
        outputModes=["text"]
    )

    agent_card = AgentCard(
        name="TradeExecutionAgent",
        description=(
            "Executes and manages trading operations with precision and reliability"
        ),
        url=f"https://{domain}/{env}/message/send",
        provider=AgentProvider(
            organization="AWS Sample Agentic Team",
            url="https://aws.amazon.com/bedrock/"
        ),
        version="1.0.0",
        documentationUrl="https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html",
        capabilities=AgentCapabilities(
            streaming=False,
            pushNotifications=False,
            stateTransitionHistory=False
        ),
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[skill],
        supportsAuthenticatedExtendedCard=False
    )

    return {
        "statusCode": 200,
        "body": agent_card.model_dump_json(),
        "headers": {"Content-Type": "application/json"}
    }
