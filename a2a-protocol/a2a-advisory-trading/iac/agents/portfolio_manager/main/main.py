import os
import json
import uuid
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
# from strands_tools import http_request
from strands import Agent as StrandsAgent
from strands.models import BedrockModel
from a2a.types import (
    Task, TaskStatus, TaskState, Message, Role, TextPart, DataPart, Artifact,
)
from a2a_core import discover_agent_cards, send_task

SYSTEM_PROMPT = (
    "You are a senior portfolio manager. Given a user's request, decompose it into structured subtasks for "
    "MarketSummary, RiskEvaluation, and ExecuteTrade as appropriate. Use strictly defined JSON formats for each task. "
    "For any missing symbol or quantity, set as 'TBD'. "
    "If the user input has the intent of buying/selling/holding shares, the analysisType of the RiskEvaluation should set to 'asset'. "
)

SKILL_MAP = {
    "MarketSummary": "market-summary",
    "RiskEvaluation": "risk-evaluation",
    "ExecuteTrade": "trade-execution"
}


def build_message_parts(user_input: str, payload: dict) -> list:
    return [
        TextPart(kind="text", text=user_input, metadata={}),
        DataPart(kind="data", data=payload, metadata={}),
    ]

class PortfolioManagerAgent:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = None):
        model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
        region_name = region or os.getenv("AWS_PRIMARY_REGION", "us-east-1")
        self.model = BedrockModel(
            model_id=model_id,
            streaming=False,
            region_name=region_name,
            max_tokens=900
        )
        self.strands_agent = StrandsAgent(
            model=self.model,
            system_prompt=SYSTEM_PROMPT
            # tools=[http_request] # tools use in local
        )

    async def analyze(self, input_data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        task_id = session_id or str(uuid.uuid4())
        print("Starting portfolio orchestration", {"task_id": task_id})

        # === PHASE 2: TRADE EXECUTION ===
        if input_data.get("trade_confirmation_phase"):
            return await self._execute_trade_phase(input_data, task_id)

        # === PHASE 1: PORTFOLIO ANALYSIS/PLANNING ===
        user_input = input_data.get("user_input")
        if not user_input:
            raise ValueError("Missing user_input for portfolio orchestration")

        plan = self._decompose_task(user_input)

        '''
             For local use only - Uncomment to use 
             ------------------------------------------------------
             Using http request tool for extra context 
             To use: in your prompt, indicate the link
             _extra_context() would extract link and summarize it.
        '''
        # extra_context =  self._extra_context(user_input)
        # for capability, payload in plan.items():
        #     if capability != "ExecuteTrade":
        #         payload["extraContext"] = extra_context

        routing_table = await discover_agent_cards()
        metadata = []
        agent_outputs = {}

        needs_symbol_resolution = (
                ("RiskEvaluation" in plan and
                 plan["RiskEvaluation"].get("analysisType") == "asset" and
                 (not plan["RiskEvaluation"].get("specificAsset") or
                  plan["RiskEvaluation"]["specificAsset"].get("symbol") == "TBD"))
                or
                ("ExecuteTrade" in plan and plan["ExecuteTrade"].get("symbol") == "TBD")
        )

        if needs_symbol_resolution:
            # --- 1. MARKET ANALYSIS TO RESOLVE SYMBOL ---
            ms_skill = SKILL_MAP["MarketSummary"]
            ms_agent_url = routing_table.get(ms_skill)
            if not ms_agent_url:
                raise ValueError(f"{ms_skill} capability not available for symbol resolution")

            ms_history = [
                Message(
                    role=Role.user,
                    parts=build_message_parts(user_input, plan["MarketSummary"]),
                    messageId=str(uuid.uuid4()),
                    kind="message",
                    contextId=task_id,
                    taskId=task_id,
                )
            ]
            market_task = Task(
                id=f"{task_id}-market-analysis",
                contextId=task_id,
                status=TaskStatus(state=TaskState.submitted, timestamp=datetime.utcnow().isoformat() + "Z"),
                history=ms_history,
                input=plan["MarketSummary"],
                artifacts=[],
                metadata={},
                kind="task"
            )
            print("Resolving symbol through market analysis")
            skill, ms_task = await self._send_to_agent(market_task, ms_skill, ms_agent_url)

            if isinstance(ms_task, Exception) or not hasattr(ms_task, "status") or ms_task.status.state != TaskState.completed:
                raise Exception(f"MarketSummary failed: {ms_task}")

            agent_outputs["MarketSummary"] = {
                "status": "completed",
                "response": getattr(ms_task, "output", None) or getattr(ms_task, "artifacts", [])
            }
            metadata.append("✅ MarketSummary completed")

            symbol = await self._extract_symbol_from_analysis(user_input, getattr(ms_task, "output", None))

            if "RiskEvaluation" in plan and plan["RiskEvaluation"].get("analysisType") == "asset":
                if "specificAsset" not in plan["RiskEvaluation"]:
                    plan["RiskEvaluation"]["specificAsset"] = {}
                plan["RiskEvaluation"]["specificAsset"]["symbol"] = symbol

                ra_skill = SKILL_MAP["RiskEvaluation"]
                ra_agent_url = routing_table.get(ra_skill)
                ra_history = [
                    Message(
                        role=Role.user,
                        parts=build_message_parts(user_input, plan["RiskEvaluation"]),
                        messageId=str(uuid.uuid4()),
                        kind="message",
                        contextId=task_id,
                        taskId=task_id,
                    )
                ]
                risk_task = Task(
                    id=f"{task_id}-risk-evaluation",
                    contextId=task_id,
                    status=TaskStatus(state=TaskState.submitted, timestamp=datetime.utcnow().isoformat() + "Z"),
                    history=ra_history,
                    input=plan["RiskEvaluation"],
                    artifacts=[],
                    metadata={},
                    kind="task"
                )

                if not ra_agent_url:
                    agent_outputs["RiskEvaluation"] = {
                        "status": "skipped",
                        "reason": "No agent found for RiskEvaluation"
                    }
                    metadata.append("⚠️ RiskEvaluation skipped — no agent found")
                else:
                    _, ra_task = await self._send_to_agent(risk_task, ra_skill, ra_agent_url)
                    if isinstance(ra_task, Task) and ra_task.status.state == TaskState.completed:
                        agent_outputs["RiskEvaluation"] = {
                            "status": "completed",
                            "response": getattr(ra_task, "output", None) or getattr(ra_task, "artifacts", [])
                        }
                        metadata.append("✅ RiskEvaluation completed")
                    else:
                        agent_outputs["RiskEvaluation"] = {
                            "status": "failed",
                            "error": str(ra_task)
                        }
                        metadata.append(f"❌ RiskEvaluation failed: {ra_task}")

            if "ExecuteTrade" in plan:
                plan["ExecuteTrade"]["symbol"] = symbol

        else:
            # --- 2. ASYNC EXECUTION FOR MARKET & RISK ---
            tasks = []
            for capability, payload in plan.items():
                if capability == "ExecuteTrade":
                    continue
                skill = SKILL_MAP.get(capability)
                print("Skill needs: ", skill)
                agent_url = routing_table.get(skill)
                print("Agent url is: ", agent_url)
                if not agent_url:
                    agent_outputs[capability] = {
                        "status": "skipped",
                        "reason": f"No agent found for capability {capability}"
                    }
                    metadata.append(f"⚠️ {capability} skipped — no agent found")
                    continue

                subtask_history = [
                    Message(
                        role=Role.user,
                        parts=build_message_parts(user_input, payload),
                        messageId=str(uuid.uuid4()),
                        kind="message",
                        contextId=task_id,
                        taskId=task_id,
                    )
                ]
                subtask = Task(
                    id=f"{task_id}-{capability.lower()}",
                    contextId=task_id,
                    status=TaskStatus(state=TaskState.submitted, timestamp=datetime.utcnow().isoformat() + "Z"),
                    history=subtask_history,
                    input=payload,
                    artifacts=[],
                    metadata={},
                    kind="task"
                )
                print("Dispatching async task", {"capability": capability, "to": agent_url})
                tasks.append(self._send_to_agent(subtask, skill, agent_url))
            results = await asyncio.gather(*tasks)
            for (capability, result) in results:
                if isinstance(result, Task) and result.status.state == TaskState.completed:
                    agent_outputs[capability] = {
                        "status": "completed",
                        "response": getattr(result, "output", None) or getattr(result, "artifacts", [])
                    }
                    metadata.append(f"✅ {capability} completed")
                else:
                    agent_outputs[capability] = {
                        "status": "failed",
                        "error": str(result)
                    }
                    metadata.append(f"❌ {capability} failed: {result}")

        # --- PHASE 1 END: IF TRADE NEEDED, PAUSE FOR USER CONFIRMATION ---
        if "ExecuteTrade" in plan:
            return {
                "status": "pending",
                "analysis_results": agent_outputs,
                "trade_details": plan["ExecuteTrade"],
                "session_id": task_id,
                "summary": " | ".join(metadata),
                "delegated_tasks": [k for k in plan.keys() if k != "ExecuteTrade"]
            }

        duration = time.time() - start_time
        print("Portfolio analysis complete", {"duration_sec": duration})
        return {
            "status": "completed",
            "summary": " | ".join(metadata),
            "delegated_tasks": list(plan.keys()),
            "agent_outputs": agent_outputs,
            "iso_time": datetime.utcnow().isoformat()
        }

    async def _send_to_agent(self, task: Task, skill: str, endpoint: str) -> Tuple[str, Task]:
        try:
            response_task = await send_task(task, endpoint, skill)
            return skill, response_task
        except Exception as e:
            return skill, e

    async def _execute_trade_phase(self, input_data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        try:
            trade_details = input_data.get("trade_details")
            user_input = input_data.get("user_input")
            if not trade_details:
                raise ValueError("Missing trade details for execution phase")
            routing_table = await discover_agent_cards()
            skill = SKILL_MAP["ExecuteTrade"]
            agent_url = routing_table.get(skill)
            if not agent_url:
                raise ValueError("ExecuteTrade capability not available")
            te_history = [
                Message(
                    role=Role.user,
                    parts=build_message_parts(user_input, trade_details),
                    messageId=str(uuid.uuid4()),
                    kind="message",
                    contextId=task_id,
                    taskId=task_id,
                )
            ]
            trade_task = Task(
                id=f"{task_id}-executetrade",
                contextId=task_id,
                status=TaskStatus(state=TaskState.submitted, timestamp=datetime.utcnow().isoformat() + "Z"),
                history=te_history,
                artifacts=[],
                metadata={},
                kind="task"
            )

            print("***Trade task:", trade_task)

            _, te_task = await self._send_to_agent(trade_task, skill, agent_url)

            if isinstance(te_task, Task) and te_task.status.state == TaskState.completed:
                response_text = None
                if te_task.status and te_task.status.message and te_task.status.message.parts:
                    for part in te_task.status.message.parts:
                        if getattr(part, 'root', None) and getattr(part.root, 'kind', None) == 'text':
                            response_text = getattr(part.root, 'text', None)
                            break
                trade_info = None
                if response_text:
                    try:
                        trade_info = json.loads(response_text)
                    except Exception:
                        trade_info = response_text

                return {
                    "status": "completed",
                    "summary": "✅ Trade execution completed",
                    "delegated_tasks": ["ExecuteTrade"],
                    "agent_outputs": {
                        "ExecuteTrade": {
                            "status": "completed",
                            "response": trade_info
                        }
                    },
                    "iso_time": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "failed",
                    "summary": f"❌ Trade execution failed: {te_task}",
                    "delegated_tasks": ["ExecuteTrade"],
                    "agent_outputs": {
                        "ExecuteTrade": {
                            "status": "failed",
                            "error": str(te_task)
                        }
                    },
                    "iso_time": datetime.utcnow().isoformat()
                }
        except Exception as e:
            print("Trade execution failed", {"error": str(e)})
            return {
                "status": "failed",
                "summary": f"Trade execution failed: {str(e)}",
                "error": str(e),
                "agent_outputs": {}
            }

    def _decompose_task(self, user_input: str) -> Dict[str, Any]:
        prompt = (
            "Based on the user's message, return appropriate task input "
            "for the following capabilities (if applicable):\n\n"
            "- MarketSummary → { sector, focus, riskFactors }\n"
            "- RiskEvaluation → { sector, analysisType, timeHorizon, capitalExposure, "
            "specificAsset: { symbol, quantity, action } }\n"
            "- ExecuteTrade → { action, symbol, quantity }\n\n"
            "Respond ONLY with a JSON payload like:\n"
            "{\n"
            "  \"MarketSummary\": {\"sector\": \"EV\", ...},\n"
            "  \"RiskEvaluation\": { \"sector\": \"technology\", \"analysisType\": \"sector\", ... },\n"
            "  \"ExecuteTrade\": { ... }\n"
            "}\n\n"
            f"User input:\n\"{user_input}\""
            "\nDo not need to give any extra information about the output, only gives the JSON payload as required."
        )
        result = str(self.strands_agent(prompt))
        try:
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Bad JSON from Claude: {str(e)}")

    async def _extract_symbol_from_analysis(self, user_input: str, market_analysis_output: Any) -> str:
        prompt = (
            "Based on the market analysis response and original user request, identify the specific stock symbol "
            "that should be used for risk assessment and trading. Return ONLY the stock symbol without any additional "
            "text, explanation, or formatting. For example, if the stock is Apple, just return: AAPL\n\n"
            f"Original user request: {user_input}\n\n"
            f"Market analysis response: {json.dumps(market_analysis_output, indent=2)}\n\n"
            "Respond with the stock symbol only."
        )
        symbol = str(self.strands_agent(prompt)).strip().upper()
        return symbol

    async def _extra_context(self, link_input: list) -> Dict[str, float]:
        """
            Note: The effectiveness of the tool depends on
            (1) user input clarity and correctness of link - link should be properly formatted
            (2) accessibility to the provided link - users need to make sure authentication is in place (if any)
        """
        prompt = (
            f"Using http request tool. "
            f"Return the 100 words summary of information for the link provided in {link_input}.\n"
            "Format required:\n"
            "{\n"
            '  "summary": <summary data>\n'
            "}\n"
        )
        try:
            result = str(self.strands_agent(prompt))
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError as e:
            print(f"Error getting summary", {"error": str(e)})
            raise ValueError(f"Failed to summarize data {str(e)}")