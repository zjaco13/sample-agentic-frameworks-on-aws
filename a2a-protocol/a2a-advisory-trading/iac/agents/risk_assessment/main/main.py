import boto3
import json
import os
import re
import io
import time
from typing import Dict, Any, Optional
from a2a_core import get_logger

logger = get_logger({"agent": "RiskAssessmentAgent"})


def build_prompt(input_data: Dict[str, Any]) -> str:
    analysis_type = input_data.get("analysisType", "general")
    sector = input_data.get("sector")
    time_horizon = input_data.get("timeHorizon", "medium")
    capital_exposure = input_data.get("capitalExposure", "moderate")
    specific_asset = input_data.get("specificAsset", {})

    if analysis_type == "asset" and specific_asset:
        symbol = specific_asset.get("symbol")
        quantity = specific_asset.get("quantity")
        action = specific_asset.get("action", "buy")
        prompt = (
            f"You are a financial risk analyst.\n"
            f"Evaluate the risk of {action}ing {quantity} shares of {symbol} "
            f"with a {time_horizon} time horizon and {capital_exposure} capital exposure.\n"
            f"Consider company fundamentals, technical indicators, and asset-specific risks.\n"
            f"Provide a JSON ONLY response in the following format:\n"
            f"{{\"score\": 85, \"rating\": \"High\", \"factors\": [\"volatility\", \"overvaluation\"], \"explanation\": \"...\"}}"
        )
    elif analysis_type == "sector" and sector:
        prompt = (
            f"You are a financial risk analyst.\n"
            f"Evaluate the risk level for the {sector} sector "
            f"with a {time_horizon} time horizon and {capital_exposure} capital exposure.\n"
            f"Consider sector-specific risks, market conditions, regulatory environment, and economic factors.\n"
            f"Provide a JSON ONLY response in the following format:\n"
            f"{{\"score\": 85, \"rating\": \"High\", \"factors\": [\"sector_volatility\", \"regulatory_risks\"], \"explanation\": \"...\"}}"
        )
    else:  # general analysis
        prompt = (
            f"You are a financial risk analyst.\n"
            f"Provide a general market risk assessment "
            f"with a {time_horizon} time horizon and {capital_exposure} capital exposure.\n"
            f"Consider macroeconomic factors, market trends, and systemic risks.\n"
            f"Provide a JSON ONLY response in the following format:\n"
            f"{{\"score\": 85, \"rating\": \"High\", \"factors\": [\"market_volatility\", \"economic_uncertainty\"], \"explanation\": \"...\"}}"
        )

    print("Prompt built", {
        "analysis_type": analysis_type,
        "sector": sector,
        "time_horizon": time_horizon,
        "capital_exposure": capital_exposure,
        "specific_asset": specific_asset if specific_asset else "N/A"
    })
    return prompt


class RiskAssessmentAgent:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = "us-east-1"):
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client(service_name="bedrock-runtime", region_name=self.region)

    def _invoke_claude_stream(self, prompt: str) -> str:
        try:
            messages = [{"role": "user", "content": [{"text": prompt}]}]

            print("Calling Claude via streaming...", {"prompt_preview": prompt[:200]})

            response_stream = self.client.converse_stream(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": 500,
                    "temperature": 0.4,
                    "topP": 0.9
                }
            )

            output = io.StringIO()
            for event in response_stream["stream"]:
                if "contentBlockDelta" in event:
                    output.write(event["contentBlockDelta"]["delta"].get("text", ""))

            full_text = output.getvalue().strip()
            print("Streaming complete", {"length": len(full_text)})
            return full_text

        except Exception as e:
            logger.error("Streaming failed", {"error": str(e)})
            raise e

    def extract_risk(self, summary: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{[\s\S]*?\}', summary)
            if not json_match:
                logger.warning("No JSON block found in risk response")
                return {"score": -1, "rating": "Unknown", "factors": [], "explanation": "Parsing failed"}

            raw_json = json_match.group()
            parsed = json.loads(raw_json)

            if isinstance(parsed, str):
                parsed = json.loads(parsed)

            return {
                "score": parsed.get("score", -1),
                "rating": parsed.get("rating", "Unknown"),
                "factors": parsed.get("factors", []),
                "explanation": parsed.get("explanation", "")
            }

        except Exception as e:
            logger.error("Tag extraction failed", {"error": str(e), "summary": summary})
            return {"score": -1, "rating": "Unknown", "factors": [], "explanation": str(e)}

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = build_prompt(input_data)
            start = time.time()

            summary = self._invoke_claude_stream(prompt)
            parsed = self.extract_risk(summary)

            duration = time.time() - start
            print("Risk analysis complete", {
                "duration_sec": duration,
                "analysis_type": input_data.get("analysisType", "general"),
                "score": parsed.get("score"),
                "rating": parsed.get("rating")
            })

            return parsed

        except Exception as e:
            logger.error("Risk analysis failed", {"error": str(e)})
            return {
                "score": -1,
                "rating": "Unknown",
                "factors": [],
                "explanation": str(e)
            }