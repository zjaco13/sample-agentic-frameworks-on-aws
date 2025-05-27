import os
import re
import json
import boto3
import asyncio
import io
import time
from datetime import datetime
from typing import Dict, Any, Optional
from a2a_core import Task, get_logger
from a2a_core import discover_agent_cards
from a2a_core import send_task

logger = get_logger({"agent": "PortfolioManagerAgent"})


class PortfolioManagerAgent:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = "us-east-1"):
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client("bedrock-runtime", region_name=self.region)

    async def analyze(self, input_data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        start_time = time.time()
        print("Starting portfolio orchestration", {"task_id": task_id})

        try:
            # Check if this is phase 2 (trade execution)
            if input_data.get("trade_confirmation_phase"):
                return await self._execute_trade_phase(input_data, task_id)

            # Phase 1: Initial Analysis
            plan = self._decompose_task(input_data)
            routing_table = await discover_agent_cards()

            print("Capabilities discovered", {"routes": list(routing_table.keys())})
            metadata = []
            agent_outputs = {}

            # Check if we need symbol resolution
            needs_symbol_resolution = False
            if "RiskEvaluation" in plan:
                risk_eval = plan["RiskEvaluation"]
                if (risk_eval.get("analysisType") == "asset" and
                        (not risk_eval.get("specificAsset") or
                         risk_eval.get("specificAsset", {}).get("symbol") == "TBD")):
                    needs_symbol_resolution = True

            if "ExecuteTrade" in plan and plan["ExecuteTrade"].get("symbol") == "TBD":
                needs_symbol_resolution = True

            # If symbol resolution needed, process market analysis first
            if needs_symbol_resolution:
                market_analysis_task = Task(
                    id=f"{task_id}-market-analysis",
                    input={"user_input": input_data.get("user_input", "")},
                    created_at=datetime.utcnow().isoformat(),
                    modified_at=datetime.utcnow().isoformat()
                )

                if "MarketSummary" not in routing_table:
                    raise ValueError("MarketSummary capability not available for symbol resolution")

                print("Resolving symbol through market analysis")
                market_analysis_result = await self._send_to_agent(
                    market_analysis_task,
                    "MarketSummary",
                    routing_table["MarketSummary"]
                )

                if isinstance(market_analysis_result[1], Exception):
                    raise market_analysis_result[1]

                # Store market analysis result
                agent_outputs["MarketSummary"] = {
                    "status": "completed",
                    "response": market_analysis_result[1].output
                }
                metadata.append("✅ MarketSummary completed")

                # Extract symbol from market analysis
                symbol = await self._extract_symbol_from_analysis(
                    input_data.get("user_input", ""),
                    market_analysis_result[1].output
                )

                # Update RiskEvaluation if present
                if "RiskEvaluation" in plan:
                    if plan["RiskEvaluation"].get("analysisType") == "asset":
                        if "specificAsset" not in plan["RiskEvaluation"]:
                            plan["RiskEvaluation"]["specificAsset"] = {}
                        plan["RiskEvaluation"]["specificAsset"]["symbol"] = symbol
                        risk_task = Task(
                            id=f"{task_id}-risk-evaluation",
                            input=plan["RiskEvaluation"],
                            created_at=datetime.utcnow().isoformat(),
                            modified_at=datetime.utcnow().isoformat()
                        )

                        if "RiskEvaluation" not in routing_table:
                            agent_outputs["RiskEvaluation"] = {
                                "status": "skipped",
                                "reason": "No agent found for RiskEvaluation"
                            }
                            metadata.append("⚠️ RiskEvaluation skipped — no agent found")
                        else:
                            risk_result = await self._send_to_agent(
                                risk_task,
                                "RiskEvaluation",
                                routing_table["RiskEvaluation"]
                            )

                            if isinstance(risk_result[1], Task) and risk_result[1].status == "completed":
                                agent_outputs["RiskEvaluation"] = {
                                    "status": "completed",
                                    "response": risk_result[1].output
                                }
                                metadata.append("✅ RiskEvaluation completed")
                            else:
                                agent_outputs["RiskEvaluation"] = {
                                    "status": "failed",
                                    "error": str(risk_result[1])
                                }
                                metadata.append(f"❌ RiskEvaluation failed: {risk_result[1]}")

                # Update ExecuteTrade if present
                if "ExecuteTrade" in plan:
                    plan["ExecuteTrade"]["symbol"] = symbol

            else:
                # Process all non-trade tasks asynchronously if no symbol resolution needed
                tasks = []
                for capability, payload in plan.items():
                    if capability == "ExecuteTrade":  # Skip trade execution in phase 1
                        continue

                    if capability not in routing_table:
                        agent_outputs[capability] = {
                            "status": "skipped",
                            "reason": f"No agent found for capability {capability}"
                        }
                        metadata.append(f"⚠️ {capability} skipped — no agent found")
                        continue

                    subtask = Task(
                        id=f"{task_id}-{capability.lower()}",
                        input=payload,
                        created_at=datetime.utcnow().isoformat(),
                        modified_at=datetime.utcnow().isoformat()
                    )

                    endpoint = routing_table[capability]
                    print("Dispatching async task", {"capability": capability, "to": endpoint})
                    tasks.append(self._send_to_agent(subtask, capability, endpoint))

                results = await asyncio.gather(*tasks)

                for capability, result in results:
                    if isinstance(result, Task) and result.status == "completed":
                        agent_outputs[capability] = {
                            "status": "completed",
                            "response": result.output
                        }
                        metadata.append(f"✅ {capability} completed")
                    else:
                        agent_outputs[capability] = {
                            "status": "failed",
                            "error": str(result)
                        }
                        metadata.append(f"❌ {capability} failed: {result}")

            # If trade execution is in the plan, return with pending status
            if "ExecuteTrade" in plan:
                return {
                    "status": "pending",
                    "analysis_results": agent_outputs,
                    "trade_details": plan["ExecuteTrade"],
                    "session_id": task_id,
                    "summary": " | ".join(metadata),
                    "delegated_tasks": [task for task in plan.keys() if task != "ExecuteTrade"]
                }

            duration = time.time() - start_time
            print("Portfolio analysis complete", {"duration_sec": duration})

            return {
                "status": "completed",
                "summary": " | ".join(metadata),
                "delegated_tasks": list(plan.keys()),
                "agent_outputs": agent_outputs
            }

        except Exception as e:
            logger.error("PortfolioManager failed", {"error": str(e)})
            return {
                "status": "failed",
                "summary": "Internal failure. Could not process portfolio request.",
                "error": str(e),
                "agent_outputs": {}
            }

    async def _send_to_agent(self, task: Task, capability: str, endpoint: str):
        try:
            response_task = await send_task(task, endpoint)
            return (capability, response_task)
        except Exception as e:
            logger.error("Subtask failed", {"capability": capability, "error": str(e)})
            return (capability, e)

    async def _execute_trade_phase(self, input_data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        try:
            trade_details = input_data.get("trade_details")
            if not trade_details:
                raise ValueError("Missing trade details for execution phase")

            routing_table = await discover_agent_cards()
            if "ExecuteTrade" not in routing_table:
                raise ValueError("ExecuteTrade capability not available")

            trade_task = Task(
                id=f"{task_id}-executetrade",
                input=trade_details,
                created_at=datetime.utcnow().isoformat(),
                modified_at=datetime.utcnow().isoformat()
            )

            trade_result = await self._send_to_agent(
                trade_task,
                "ExecuteTrade",
                routing_table["ExecuteTrade"]
            )

            if isinstance(trade_result[1], Task) and trade_result[1].status == "completed":
                return {
                    "status": "completed",
                    "summary": "✅ Trade execution completed",
                    "delegated_tasks": ["ExecuteTrade"],
                    "agent_outputs": {
                        "ExecuteTrade": {
                            "status": "completed",
                            "response": trade_result[1].output
                        }
                    }
                }
            else:
                return {
                    "status": "failed",
                    "summary": f"❌ Trade execution failed: {trade_result[1]}",
                    "delegated_tasks": ["ExecuteTrade"],
                    "agent_outputs": {
                        "ExecuteTrade": {
                            "status": "failed",
                            "error": str(trade_result[1])
                        }
                    }
                }

        except Exception as e:
            logger.error("Trade execution failed", {"error": str(e)})
            return {
                "status": "failed",
                "summary": f"Trade execution failed: {str(e)}",
                "error": str(e),
                "agent_outputs": {}
            }

    async def _extract_symbol_from_analysis(self, user_input: str, market_analysis_output: Dict[str, Any]) -> str:
        prompt = (
            "Based on the market analysis response and original user request, identify the specific stock symbol "
            "that should be used for risk assessment and trading. Return ONLY the stock symbol without any additional "
            "text, explanation, or formatting. For example, if the stock is Apple, just return: AAPL\n\n"
            f"Original user request: {user_input}\n\n"
            f"Market analysis response: {json.dumps(market_analysis_output, indent=2)}\n\n"
            "Respond with the stock symbol only."
        )

        print("Sending prompt to Bedrock for symbol analysis")
        try:
            output = self._invoke_claude(prompt)

            # Clean the output and extract symbol
            symbol = output.strip().upper()

            # Basic validation for stock symbol format
            if not re.match(r'^[A-Z]{1,5}$', symbol):
                print(f"Warning: Unexpected symbol format received: {symbol}")
                # Try to extract symbol if there's additional text
                match = re.search(r'[A-Z]{1,5}', symbol)
                if match:
                    symbol = match.group()
                else:
                    raise ValueError(f"Could not extract valid symbol from: {symbol}")

            print(f"Extracted symbol: {symbol}")
            return symbol

        except Exception as e:
            logger.error("Symbol extraction failed", {"error": str(e), "output": output if 'output' in locals() else None})
            raise ValueError(f"Failed to extract symbol: {str(e)}")

    def _decompose_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_input = input_data.get("user_input", "").strip()
        if not user_input:
            raise ValueError("Missing user_input in input_data")

        prompt = (
            "You are a financial assistant. Based on the user's message, return appropriate task input "
            "for the following capabilities (if applicable):\n\n"
            "- MarketSummary → { sector, focus, riskFactors }\n"
            "- RiskEvaluation → { sector, analysisType, timeHorizon, capitalExposure, "
            "specificAsset: { symbol, quantity, action } }\n"
            "- ExecuteTrade → { action, symbol, quantity }\n\n"
            "For RiskEvaluation, analysisType can be one of the following:\n"
            "- 'sector': Analysis of an entire industry sector's risks (e.g., technology, healthcare). "
            "Do not include specificAsset for sector analysis.\n"
            "- 'asset': Analysis of a specific stock or security. Must include specificAsset with "
            "symbol, quantity, and action details. If either quantity or symbol is missing, assign the value of TBD for the field. \n"
            "- 'general': Overall market or portfolio risk assessment without focus on specific "
            "sectors or assets. Do not include specificAsset for general analysis.\n\n"
            "Respond ONLY with a JSON payload like:\n"
            "{\n"
            "  \"MarketSummary\": {\"sector\": \"EV\", ...},\n"
            "  \"RiskEvaluation\": { \"sector\": \"technology\", \"analysisType\": \"sector\", ... },\n"
            "  \"ExecuteTrade\": { ... }\n"
            "}\n\n"
            f"User input:\n\"{user_input}\""
        )

        print("Sending prompt to Bedrock", {"prompt_preview": prompt[:300]})
        output = self._invoke_claude(prompt)

        match = re.search(r"\{[\s\S]*\}", output)
        if not match:
            raise ValueError("Claude output missing JSON")

        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            raise ValueError(f"Bad JSON from Claude: {str(e)}")

    def _invoke_claude(self, prompt: str) -> str:
        try:
            messages = [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ]

            print("Calling Claude via streaming...", {"prompt_preview": prompt[:200]})

            response_stream = self.client.converse_stream(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": 500,
                    "temperature": 0.5,
                    "topP": 0.9
                }
            )

            output = io.StringIO()
            for event in response_stream["stream"]:
                if "contentBlockDelta" in event:
                    chunk = event["contentBlockDelta"]["delta"].get("text", "")
                    output.write(chunk)

            full_text = output.getvalue().strip()
            print("Streaming complete", {"length": len(full_text)})
            return full_text

        except Exception as e:
            logger.error("Claude streaming failed", {"error": str(e)})
            raise e