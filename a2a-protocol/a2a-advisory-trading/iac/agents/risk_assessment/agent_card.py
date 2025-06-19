from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentProvider

def lambda_handler(event, context):
    domain = event['requestContext']['domainName']
    env = event['requestContext'].get('env', 'dev')

    skill = AgentSkill(
        id="risk-evaluation",
        name="Risk Evaluation",
        description=(
            "Performs comprehensive risk assessments for financial instruments and markets, "
            "analyzing potential threats, vulnerabilities, and risk factors. Provides actionable "
            "insights for risk-aware trading decisions. Assess risk of investment in relation to a "
            "investor profile or individual financial context."
        ),
        tags=["finance", "risk", "analysis", "trading", "aws"],
        examples=[
            "Evaluate the risks in the oil and gas sector given current market conditions.",
            "Assess the risk factors for emerging market investments.",
            "Evaluate the risk of investment for an individual knowing their investment profile."
        ],
        inputModes=["text"],
        outputModes=["text"]
    )

    agent_card = AgentCard(
        name="RiskAssessmentAgent",
        description="Provides detailed risk evaluations and assessments using Amazon Bedrock foundation models.",
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
