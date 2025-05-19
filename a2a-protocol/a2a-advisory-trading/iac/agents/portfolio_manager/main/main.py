import json
import os
import re
import boto3
from datetime import datetime
from typing import Dict, Any, Optional
from a2a_core import get_logger
from a2a_core import Task
from a2a_core import discover_agent_cards
from a2a_core import send_task

logger = get_logger({"agent": "PortfolioManagerAgent"})


class PortfolioManagerAgent:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = "us-east-1"):
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client("bedrock-runtime", region_name=self.region)

    def analyze(self, input_data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        print("Analyzing user input via Claude", {"input": input_data})

        try:
            task_plan = self._decompose_task(input_data)
            print("Task plan decomposition complete", {"task_plan": task_plan})
            routing_table = discover_agent_cards()
            print("Discovered routing table", {"routing_table": routing_table})

            agent_outputs = {}
            agent_summary = []

            for capability, payload in task_plan.items():
                if capability not in routing_table:
                    agent_outputs[capability] = {
                        "status": "skipped",
                        "reason": f"No agent found for capability: {capability}"
                    }
                    agent_summary.append(f"⚠️ Skipped `{capability}` – no agent found.")
                    continue

                endpoint = routing_table[capability]
                subtask_id = f"{task_id}-{capability.lower()}"
                print("Routing subtask", {"capability": capability, "to": endpoint})

                subtask = Task(
                    id = subtask_id,
                    input = payload,
                    created_at = datetime.now().isoformat(),
                    modified_at = datetime.now().isoformat()
                )

                try:
                    result = send_task(subtask, endpoint)
                    print("Task sent successfully")
                    agent_outputs[capability] = {
                        "status": "completed",
                        "response": result
                    }
                    print("Checking agent_output:", agent_outputs)
                    agent_summary.append(f"✅ `{capability}` processed successfully.")
                    print("Checking agent_summary:", agent_summary)

                except Exception as e:
                    agent_outputs[capability] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    print("Task sent failed")
                    agent_summary.append(f"❌ `{capability}` failed: {str(e)}")

            print({
                "summary": " | ".join(agent_summary),
                "delegated_tasks": list(task_plan.keys()),
                "agent_outputs": agent_outputs
            })

            return {
                "summary": " | ".join(agent_summary),
                "delegated_tasks": list(task_plan.keys()),
                "agent_outputs": agent_outputs
            }

        except Exception as e:
            logger.error("Portfolio manager failed", {"error": str(e)})
            return {
                "summary": "Unable to process your request due to internal error.",
                "error": str(e),
                "agent_outputs": {}
            }

    def _decompose_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        user_input = input_data.get("user_input", "").strip()
        if not user_input:
            raise ValueError("Missing user_input field")

        prompt = (
            "You are a portfolio decision assistant. Given the user's request, decompose the task "
            "into subtasks for the appropriate agents. Available capabilities:\n\n"
            "- MarketSummary: requires { sector, focus, riskFactors }\n"
            "- RiskEvaluation: requires { action, symbol, quantity, sector, priceVolatility, timeHorizon, marketConditions, capitalExposure }\n"
            "- ExecuteTrade: requires { symbol, quantity, action }\n\n"
            "Respond ONLY in JSON with the appropriate payloads for each capability. Example:\n"
            "{\n"
            "  \"MarketSummary\": {\"sector\": \"energy\", \"focus\": \"growth outlook\", \"riskFactors\": [\"regulation\", \"supply\"]},\n"
            "  \"RiskEvaluation\": {\"action\": \"Buy\", \"symbol\": \"TSLA\", \"quantity\": 25, \"sector\": \"EV\", \"priceVolatility\": \"high\", \"timeHorizon\": \"short-term\", \"marketConditions\": \"uncertain\", \"capitalExposure\": \"moderate\"},\n"
            "  \"ExecuteTrade\": {\"action\": \"Buy\", \"symbol\": \"TSLA\", \"quantity\": 25}\n"
            "}\n\n"
            f"User request:\n\"{user_input}\""
        )

        print("Sending prompt to Claude for decomposition", {"prompt": prompt[:300]})
        raw_response = self._invoke_claude(prompt)
        print("Raw Claude output", {"text": raw_response})

        json_match = re.search(r'\{[\s\S]*\}', raw_response)
        if not json_match:
            raise ValueError("Claude did not return valid JSON.")

        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Claude output", {"error": str(e)})
            raise ValueError("Invalid JSON format returned by Claude.")

    def _invoke_claude(self, prompt: str) -> str:
        try:
            body = {
                "anthropic_version": "bedrock-2024-02-29",
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.5,
                "top_p": 0.9
            }

            response = self.client.converse(
                modelId=self.model_id,
                messages=body["messages"],
                inferenceConfig={"temperature": body["temperature"], "topP": body["top_p"]},
            )

            return response["output"]["message"]["content"][0]["text"].strip()

        except Exception as e:
            logger.error("Claude model invocation failed", {"error": str(e)})
            raise
