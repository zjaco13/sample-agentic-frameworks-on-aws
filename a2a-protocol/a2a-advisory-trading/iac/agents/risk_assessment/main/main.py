import boto3
import json
import os
import re
from typing import Dict, Any, Optional
from a2a_core import get_logger

logger = get_logger({"agent": "RiskAssessmentAgent"})


def build_prompt(input_data: Dict[str, Any]) -> str:
    symbol = input_data.get("symbol", "AAPL")
    quantity = input_data.get("quantity", 50)
    sector = input_data.get("sector", "technology")
    sentiment = input_data.get("sentiment", "neutral")

    prompt = (
        f"You are a financial risk analyst.\n"
        f"Evaluate the risk of buying {quantity} shares of {symbol} in the {sector} sector.\n"
        f"The current market sentiment is {sentiment}.\n"
        f"Analyze macroeconomic and sector-specific risks, recent news, and valuation.\n"
        f"Provide a JSON ONLY response in the following format:\n"
        f"{{\"score\": 85, \"rating\": \"High\", \"factors\": [\"volatility\", \"overvaluation\"], \"explanation\": \"...\"}}"
    )

    print("Prompt built", {"symbol": symbol, "quantity": quantity, "sector": sector, "sentiment": sentiment})
    return prompt


class RiskAssessmentAgent:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = "us-east-1"):
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client(service_name="bedrock-runtime", region_name=self.region)

    def converse(self, messages: list) -> str:
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={"temperature": 0.4, "topP": 0.9},
                additionalModelRequestFields={"top_k": 50}
            )
            return response["output"]["message"]["content"][0]["text"].strip()
        except Exception as e:
            logger.error("Bedrock converse() failed", {"error": str(e)})
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
            print("Risk analysis started", {"input": input_data})

            messages = [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ]
            raw_response = self.converse(messages)
            print("Raw risk output received", {"preview": raw_response[:120]})

            return self.extract_risk(raw_response)

        except Exception as e:
            logger.error("Risk analysis failed", {"error": str(e)})
            return {
                "score": -1,
                "rating": "Unknown",
                "factors": [],
                "explanation": str(e)
            }
