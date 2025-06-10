import os
import sys
import uuid
import json
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

current_dir = Path(__file__).parent
root_dir = current_dir.parent
sys.path.insert(0, str(root_dir))

from config import setup_paths
setup_paths()

from iac.agents.portfolio_manager.main.main import PortfolioManagerAgent

load_dotenv()

app = FastAPI()

def to_dict(obj):
    # Recursively convert Pydantic models to dicts
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_dict(item) for item in obj]
    else:
        return obj

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/.well-known/agent.json")
async def agent_card():
    from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentProvider

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
        url="http://localhost:8003/message/send",
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
    return JSONResponse(json.loads(agent_card.model_dump_json()))

# Accept raw JSON, which should be either phase 1 or phase 2
# Either: { "user_input": "...." } OR { "trade_confirmation_phase": true, "trade_details": {...} }
@app.post("/message/send")
async def handle_task(request: Request):
    body = await request.json()
    session_id = body.get("session_id") or body.get("contextId") or str(uuid.uuid4())
    agent = PortfolioManagerAgent(
        model_id=os.getenv("BEDROCK_MODEL_ID"),
        region=os.getenv("AWS_REGION")
    )

    try:
        result = await agent.analyze(body, session_id)
        status_code = 200 if result.get("status") == "completed" else 202 if result.get("status") == "pending" else 500
        return JSONResponse(to_dict(result), status_code=status_code)  # <-- fix here
    except Exception as e:
        print("Error in local_server_pm:", e)
        return JSONResponse({
            "status": "failed",
            "error": str(e)
        }, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("local_server_pm:app", host="0.0.0.0", port=8003, reload=True)
