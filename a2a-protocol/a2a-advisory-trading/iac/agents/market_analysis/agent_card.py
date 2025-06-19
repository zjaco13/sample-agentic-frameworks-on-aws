from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentProvider

def lambda_handler(event, context):
    domain = event['requestContext']['domainName']
    env = event['requestContext'].get('env', 'dev')
    skill = AgentSkill(
        id="market-summary",
        name="Market Summary",
        description=(
            "Generates concise, clear summaries of financial markets for a given sector, "
            "including sentiment analysis and major trends. Useful for portfolio insights and trade decisions."
        ),
        tags=["finance", "summary", "sentiment", "market analysis", "aws"],
        examples=[
            "Summarize the outlook for the technology sector.",
            "Give me a bullish or bearish summary for the US stock market in oil and gas industry."
        ],
        inputModes=["text"],
        outputModes=["text"]
    )
    agent_card = AgentCard(
        name="MarketAnalysisAgent",
        description="Provides market analysis summaries and sentiment insights using Amazon Bedrock foundation models.",
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
        supportsAuthenticatedExtendedCard=False,
    )
    return {
        "statusCode": 200,
        "body": agent_card.model_dump_json(),
        "headers": {"Content-Type": "application/json"}
    }
