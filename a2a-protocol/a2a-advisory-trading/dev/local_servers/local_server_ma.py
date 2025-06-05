import os
import sys
from pathlib import Path

current_dir = Path(__file__).parent
root_dir = current_dir.parent
sys.path.insert(0, str(root_dir))

from config import setup_paths
setup_paths()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from iac.agents.market_analysis.main.main import MarketAnalysisAgent
from datetime import datetime
from a2a_core import Task

load_dotenv()

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/.well-known/agent.json")
async def agent_card():
    card = {
        "id": "market-analysis-agent",
        "name": "MarketAnalysisAgent",
        "description": "Provides market analysis summaries and sentiment insights via Bedrock.",
        "protocol": "A2A/1.0",
        "skills": ["MarketSummary"],
        "endpoints": {
            "send": "http://localhost:8000/task"
        },
        "metadata": {
            "streaming": True,
            "provider": "Bedrock/Anthropic",
            "modelId": os.getenv("BEDROCK_MODEL_ID"),
            "region": os.getenv("AWS_REGION")
        }
    }
    return JSONResponse(card)

@app.post("/task")
async def handle_task(request: Request):
    body = await request.json()
    task = Task.from_dict(body.get("task"))

    agent = MarketAnalysisAgent(
        model_id=os.getenv("BEDROCK_MODEL_ID"),
        region=os.getenv("AWS_REGION"),
    )
    result = agent.analyze(task.input or {})

    task.output = result
    task.status = "completed"
    task.modified_at = datetime.now().isoformat()

    return JSONResponse(task.to_dict())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("local_server_ma:app", host="0.0.0.0", port=8000, reload=True)
