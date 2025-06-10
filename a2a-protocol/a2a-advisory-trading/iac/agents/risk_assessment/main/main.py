import os
import uuid
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from strands import Agent as StrandsAgent
from strands.models import BedrockModel
# from strands_tools import python_repl
from a2a.types import Task, TaskStatus, TaskState, Message, Artifact, Role, TextPart, DataPart

SYSTEM_PROMPT = (
    "You are a financial risk analyst."
    "Provide clear, factual, and structured risk assessments only in the requested format."
)

# Note: Enable MCP for ticker price - local use only
# BYPASS_TOOL_CONSENT = "true"

def extract_user_input_from_task(task: Task) -> Dict[str, Any]:
    _input_data = {}

    print(f"DEBUG: Received task: {task}")

    if not task or not task.history:
        print("DEBUG: No task or history found")
        return {"error": "No task or history found"}

    # Find the most recent user message
    user_messages = [msg for msg in task.history if msg.role.value == "user"]
    if not user_messages:
        print("DEBUG: No user messages found")
        return {"error": "No user messages found"}

    latest_user_message = user_messages[-1]
    print(f"DEBUG: Latest user message: {latest_user_message}")

    # Process message parts
    for part in latest_user_message.parts:
        print(f"DEBUG: Processing part: {part}")
        if part.root.kind == "text":
            _input_data["userContext"] = part.root.text
        if part.root.kind == "data" and part.root.data:
            # Extract main data fields
            data = part.root.data
            _input_data["analysisType"] = data.get("analysisType", "general")
            _input_data["sector"] = data.get("sector", "UNKNOWN_SECTOR")
            _input_data["timeHorizon"] = data.get("timeHorizon", "medium")
            _input_data["capitalExposure"] = data.get("capitalExposure", "moderate")
            _input_data["specificAsset"] = data.get("specificAsset", {})
            # Extract extra context if present
            if "extraContext" in data:
                _input_data["extraContext"] = data["extraContext"]

    print(f"DEBUG: Extracted data: {_input_data}")
    return _input_data

class RiskAssessmentAgent:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = "us-east-1"):
        model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
        region_name = region or os.getenv("AWS_PRIMARY_REGION", "us-east-1")
        self.model = BedrockModel(
            model_id=model_id,
            streaming=True,
            region_name=region_name,
            max_tokens=600
        )
        self.strands_agent = StrandsAgent(
            model=self.model,
            system_prompt=SYSTEM_PROMPT,
            # tools=[python_repl] # tools use in local
        )

    def build_prompt(self, input_: Dict[str, Any]) -> str:
        user_context = input_.get("userContext", None)
        extra_context = input_.get("extraContext", None)
        analysis_type = input_.get("analysisType", "general")
        sector = input_.get("sector", "UNKNOWN_SECTOR")
        time_horizon = input_.get("timeHorizon", "medium")
        capital_exposure = input_.get("capitalExposure", "moderate")
        specific_asset = input_.get("specificAsset", {})

        if analysis_type == "asset" and specific_asset:
            symbol = specific_asset.get("symbol", "UNKNOWN")
            quantity = specific_asset.get("quantity", "TBD")
            action = specific_asset.get("action", "buy")
            prompt = (
                f"You are a financial risk analyst. Analyze the risk for the following investment scenario:\n\n"
                f"Asset Details:\n"
                f"- Action: {action.upper()}\n"
                f"- Symbol: {symbol}\n"
                f"- Quantity: {quantity} shares\n"
                f"- Sector: {sector}\n"
                f"- Time Horizon: {time_horizon}\n"
                f"- Capital Exposure: {capital_exposure}\n"
                f"Additional Context: {user_context if user_context else 'No additional context provided'}\n\n"
                f"Provide a risk assessment that considers:\n"
                f"1. Company-specific factors (financials, management, market position)\n"
                f"2. Sector dynamics affecting {symbol}\n"
                f"3. Market conditions relevant to this {action} decision\n"
                f"4. Time horizon implications\n\n"
                f"You MUST respond ONLY with a JSON object in this exact format:\n"
                f"{{\"score\": <0-100>, \"rating\": \"High|Moderate|Low\", \"factors\": [\"<factor1>\", \"<factor2>\"], "
                f"\"explanation\": \"One short paragraph with specific facts about {symbol} and its current situation.\"}}\n\n"
                f"Focus solely on {symbol} - do not mention other companies or assets in your assessment."
            )

        elif analysis_type == "sector" and sector:
            prompt = (
                f"You are a financial risk analyst. Provide a comprehensive risk assessment for the following sector:\n\n"
                f"Analysis Parameters:\n"
                f"- Sector: {sector}\n"
                f"- Time Horizon: {time_horizon}\n"
                f"- Capital Exposure: {capital_exposure}\n"
                f"Additional Context: {user_context if user_context else 'No additional context provided'}\n\n"
                f"Analyze the current risk profile considering:\n"
                f"1. Major trends affecting the {sector} sector\n"
                f"2. Regulatory environment and potential changes\n"
                f"3. Economic factors specifically impacting {sector}\n"
                f"4. Competitive dynamics within the sector\n"
                f"5. Technology and innovation impacts\n\n"
                f"You MUST respond ONLY with a JSON object in this exact format:\n"
                f"{{\"score\": <0-100>, \"rating\": \"High|Moderate|Low\", \"factors\": [\"<factor1>\", \"<factor2>\"], "
                f"\"explanation\": \"One short paragraph with specific facts about the {sector} sector's current situation.\"}}\n\n"
                f"Focus exclusively on the {sector} sector - do not discuss other sectors in your assessment."
            )
        else:
            prompt = (
                f"You are a financial risk analyst. Based on current market conditions and the following parameters:\n"
                f"- Time horizon: {time_horizon}\n"
                f"- Capital exposure level: {capital_exposure}\n"
                f"Additional context (if provided): {user_context}\n\n"
                f"Provide a general market risk assessment that considers major economic indicators, "
                f"market trends, and global factors. Even without specific user context, you should "
                f"analyze current market conditions and provide a risk assessment.\n\n"
                f"You MUST respond ONLY with a JSON object in this format:\n"
                f"{{\"score\": <0-100>, \"rating\": \"High|Moderate|Low\", \"factors\": [\"<factor1>\", \"<factor2>\"], "
                f"\"explanation\": \"Short summary of current market-wide risk drivers.\"}}\n\n"
                f"Provide your assessment now:"
            )

        print("Prompt built", {
            "analysis_type": analysis_type,
            "sector": sector,
            "time_horizon": time_horizon,
            "capital_exposure": capital_exposure,
            "specific_asset": specific_asset if specific_asset else "N/A"
        })

        '''
        For local use only
        '''
        if extra_context:
            prompt += f" Here is more context: {extra_context}."
        return prompt

    def analyze(self, task: Task) -> Task:
        prompt_input = extract_user_input_from_task(task)

        prompt = self.build_prompt(prompt_input)

        try:
            response = self.strands_agent(prompt)
            assessment = str(response)

            """
                Primary Note: 
                As of June 2025, this tool requires explicit approval from user before execution. 
                As a result, this integration only available in local for security and stability in deployed environment. 
                Check TOOL_SPEC in https://github.com/strands-agents/tools/blob/main/src/strands_tools/python_repl.py   
                ------------------------------------------------------
                Secondary Note: 
                To have price data visible in cli.py: (1) add price data to assessment results and (2) update cli.py format response 
            """
            # if prompt_input.get("analysisType") == "asset" and prompt_input.get("specificAsset"):
            #     symbol = prompt_input.get("specificAsset").get("symbol")
            #     if symbol != "UNKNOWN":
            #         price_data = self._ticker_price(symbol)
            #         print(price_data)

            parts = [
                {
                    "kind": "text",
                    "text": assessment,
                    "metadata": {}
                }
            ]

            artifact = Artifact(
                artifactId=str(uuid.uuid4()),
                parts=parts,
                name="Risk Assessment",
                description="Risk assessment generated by LLM"
            )

            msg = Message(
                role="agent",
                parts=[TextPart(kind="text", text="Risk assessment successfully generated.", metadata={})],
                messageId=str(uuid.uuid4()),
                kind="message",
                taskId=task.id,
                contextId=getattr(task, "contextId", None)
            )

            status = TaskStatus(
                state=TaskState.completed,
                message=msg,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

            task.status = status
            task.artifacts = task.artifacts or []
            task.artifacts.append(artifact)
            if hasattr(task, "kind"):
                task.kind = "task"
            else:
                setattr(task, "kind", "task")
        except Exception as e:
            error_parts = [
                {
                    "kind": "text",
                    "text": str(e),
                    "metadata": {}
                }
            ]

            error_artifact = Artifact(
                artifactId=str(uuid.uuid4()),
                parts=error_parts,
                name="Error",
                description="Error encountered during risk assessment"
            )

            error_message = Message(
                role="agent",
                parts=error_parts,
                messageId=str(uuid.uuid4()),
                kind="message",
                taskId=task.id,
                contextId=getattr(task, "contextId", None)
            )

            status = TaskStatus(
                state=TaskState.failed,
                message=error_message,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

            task.status = status
            task.artifacts = task.artifacts or []
            task.artifacts.append(error_artifact)
            if hasattr(task, "kind"):
                task.kind = "task"
            else:
                setattr(task, "kind", "task")
        return task

    def _ticker_price(self, symbol: str) -> Dict[str, float]:
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
            print(f"Error getting ticker price for {symbol}", {"error": str(e)})
            raise ValueError(f"Failed to get price for {symbol}: {str(e)}")