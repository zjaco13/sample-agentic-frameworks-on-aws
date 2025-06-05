import os
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from strands import Agent as StrandsAgent
from strands.models import BedrockModel
from strands_tools import current_time
# from strands_tools import python_repl
# from strands_tools import http_request
from a2a_core import Task, get_logger
from a2a_core import discover_agent_cards
from a2a_core import send_task

logger = get_logger({"agent": "PortfolioManagerAgent"})

SYSTEM_PROMPT = (
    "You are a senior portfolio manager. Given a user's request, decompose it into structured subtasks for "
    "MarketSummary, RiskEvaluation, and ExecuteTrade as appropriate. Use strictly defined JSON formats for each task. "
    "For any missing symbol or quantity, set as 'TBD'. "
    "If the user input has the intent of buying/selling/holding shares, the analysisType of the RiskEvaluation should set to 'asset'. "
)


# Note: Enable MCP for ticker price - local use only
# BYPASS_TOOL_CONSENT = "true"

class PortfolioManagerAgent:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = None):
        model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
        region_name = region or os.environ.get("AWS_PRIMARY_REGION", "us-east-1")

        self.model = BedrockModel(
            model_id=model_id,
            streaming=False,
            region_name=region_name,
            max_tokens=900
        )
        self.strands_agent = StrandsAgent(
            model=self.model,
            system_prompt=SYSTEM_PROMPT,
            # tools=[current_time, http_request, python_repl()] # tools use in local
            tools=[current_time]
        )

    async def analyze(self, input_data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        start_time = time.time()
        print("Starting portfolio orchestration", {"task_id": task_id})

        try:
            # Check if this is phase 2 (trade execution)
            if input_data.get("trade_confirmation_phase"):
                return await self._execute_trade_phase(input_data, task_id)

            # Phase 1: Initial Analysis
            plan = self._decompose_task(input_data)
            '''
                http_request MCP: For local use only
            '''
            # user_link = self._user_http_link(input_data)
            # extra_context = {}
            # if user_link.get("found_links") and user_link.get("valid"):
            #     links = user_link.get("found_links")
            #     for i in range(len(links)):
            #         extra_context[f"link{i+1}"] = self._extra_context(links[i])

            routing_table = await discover_agent_cards()

            for capability, payload in plan.items():
                if capability != "ExecuteTrade":
                    payload["userContext"] = input_data
                    '''
                        For local use only 
                    '''
                    # payload["extraContext"] = extra_context

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
                    input=plan["MarketSummary"],
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
                '''
                    Note: 
                    As of June 2025, this tool requires explicit approval from user before execution. 
                    As a result, this integration only available in local for security and stability in deployed environment. 
                    Check TOOL_SPEC in https://github.com/strands-agents/tools/blob/main/src/strands_tools/python_repl.py
                '''
                # Price MCP: For local use only
                # symbol = plan["ExecuteTrade"].get("symbol")
                # if symbol != "TBD":
                #     try:
                #         price_data = await self._ticker_price(symbol)
                #         plan["ExecuteTrade"].update(price_data)
                #         print("\nPrice check completed", {"price_data": price_data})
                #     except Exception as e:
                #         logger.warning(f"Price check failed for {symbol}", {"error": str(e)})

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

            try:
                time_data = await self._current_time()
                return {
                    "status": "completed",
                    "summary": " | ".join(metadata),
                    "delegated_tasks": list(plan.keys()),
                    "agent_outputs": agent_outputs,
                    "iso_time": time_data["timestamp"]
                }
            except Exception as e:
                logger.warning("MCP time check failed, using system time", {"error": str(e)})
                return {
                    "status": "completed",
                    "summary": " | ".join(metadata),
                    "delegated_tasks": list(plan.keys()),
                    "agent_outputs": agent_outputs,
                    "iso_time": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error("PortfolioManager failed", {"error": str(e)})
            return {
                "status": "failed",
                "summary": "Internal failure. Could not process portfolio request.",
                "error": str(e),
                "agent_outputs": {}
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
                try:
                    time_data = await self._current_time()
                    return {
                        "status": "completed",
                        "summary": "✅ Trade execution completed",
                        "delegated_tasks": ["ExecuteTrade"],
                        "agent_outputs": {
                            "ExecuteTrade": {
                                "status": "completed",
                                "response": trade_result[1].output,
                                "iso_time": time_data["timestamp"]
                            }
                        }
                    }
                except Exception as e:
                    logger.warning("MCP time check failed, using system time", {"error": str(e)})
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
        symbol = str(self.strands_agent(prompt)).strip().upper()
        print(f"Extracted symbol: {symbol}")
        return symbol

    def _decompose_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_input = input_data.get("user_input", "").strip()
        if not user_input:
            raise ValueError("Missing user_input in input_data")

        prompt = (
            "Based on the user's message, return appropriate task input "
            "for the following capabilities (if applicable):\n\n"
            "- MarketSummary → { sector, focus, riskFactors }\n"
            "- RiskEvaluation → { sector, analysisType, timeHorizon, capitalExposure, "
            "specificAsset: { symbol, quantity, action } }\n"
            "- ExecuteTrade → { action, symbol, quantity }\n\n"
            "For RiskEvaluation, analysisType can be one of the following:\n"
            "- 'sector': Analysis of an entire industry sector's risks (e.g., technology, healthcare). "
            "Do not include specificAsset for sector analysis.\n"
            "- 'asset': Analysis of a specific stock or security. Must include specificAsset with "
            "symbol, quantity, and action details - assign the value of TBD for any missing field. \n"
            "- 'general': Overall market or portfolio risk assessment without focus on specific "
            "sectors or assets. If user input has the intention of buying or selling, then 'analysisType' of RiskEvaluation has to be 'asset'. \n"
            "Do not include 'specificAsset' for 'general' analysisType.\n\n"
            "Respond ONLY with a JSON payload like:\n"
            "{\n"
            "  \"MarketSummary\": {\"sector\": \"EV\", ...},\n"
            "  \"RiskEvaluation\": { \"sector\": \"technology\", \"analysisType\": \"sector\", ... },\n"
            "  \"ExecuteTrade\": { ... }\n"
            "}\n\n"
            f"User input:\n\"{user_input}\""
            "\nDo not need to give any extra information about the output, only gives the JSON payload as required."
        )

        print("Sending prompt to Bedrock", {"prompt_preview": prompt[:300]})
        result = str(self.strands_agent(prompt))
        try:
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Bad JSON from Claude: {str(e)}")

    def _user_http_link(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_input = input_data.get("user_input", "").strip()
        if not user_input:
            raise ValueError("Missing user_input in input_data")

        prompt = (
            "Based on the user's message, analyze and extract any URLs or web links. "
            "Return a JSON object with the following structure:\n"
            "{\n"
            "  'found_links': [list of extracted URLs],\n"
            "  'context': 'brief description of what these links represent',\n"
            "  'valid': boolean indicating if links are properly formatted,\n"
            "  'source_text': 'the relevant text segment containing the link'\n"
            "}\n"
            "If no links are found, return:\n"
            "{\n"
            "  'found_links': [],\n"
            "  'context': 'no links found',\n"
            "  'valid': false,\n"
            "  'source_text': null\n"
            "}\n"
            f"Analyze this input: {user_input}"
        )

        result = str(self.strands_agent(prompt))
        try:
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Bad JSON response: {str(e)}")


    async def _current_time(self) -> Dict[str, str]:
        prompt = (
            "Use the current_time tool to get the current time and return ONLY a strict JSON with this exact structure:\n"
            "{\n"
            '  "timestamp": "<ISO_8601_TIME>"\n'
            "}\n"
        )
        try:
            result = str(self.strands_agent(prompt))
            result = result.replace("Tool #1: current_time\n", "").strip()
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError as e:
            logger.error("Error getting current time", {"error": str(e)})
            return {
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _ticker_price(self, symbol: str) -> Dict[str, float]:
        prompt = (
            f"Using historical data from Yahoo Finance. "
            f"Return ONLY a strict JSON with the price for {symbol}.\n"
            "Format required:\n"
            "{\n"
            '  "stock_price": <numerical_value>\n'
            "}\n"
        )
        try:
            result = str(self.strands_agent(prompt))
            parsed = json.loads(result)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Error getting ticker price for {symbol}", {"error": str(e)})
            raise ValueError(f"Failed to get price for {symbol}: {str(e)}")

    async def _extra_context(self, link_input: list) -> Dict[str, float]:
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
            logger.error(f"Error getting summary", {"error": str(e)})
            raise ValueError(f"Failed to summarize data {str(e)}")