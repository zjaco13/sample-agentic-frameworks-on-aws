import os
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentProvider

def lambda_handler(event, context):
    domain = event['requestContext']['domainName']
    env = event['requestContext'].get('env', 'dev')

    skill = AgentSkill(
        id="portfolio-orchestration",
        name="Portfolio Orchestration",
        description=(
            "Orchestrates comprehensive portfolio management by coordinating market analysis, "
            "risk assessment, and trade execution. Analyzes user investment goals and constraints "
            "to provide holistic portfolio insights and recommendations through coordinated "
            "agent interactions."
        ),
        tags=["finance", "portfolio", "orchestration", "analysis", "aws"],
        examples=[
            "Analyze the current industry and its relevant risk ",
            "Considering my personal financial profile, what is the market situation and my risk to invest in 100 shares in XYZ?",
            "Coordinate risk assessment and trade execution for portfolio rebalancing"
        ],
        inputModes=["text"],
        outputModes=["text"]
    )

    agent_card = AgentCard(
        name="PortfolioManagerAgent",
        description=(
            "Orchestrates portfolio management decisions by coordinating multiple specialized agents "
            "using Amazon Bedrock foundation models. Provides comprehensive portfolio insights through "
            "synchronized market analysis, risk assessment, and trade execution."
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
