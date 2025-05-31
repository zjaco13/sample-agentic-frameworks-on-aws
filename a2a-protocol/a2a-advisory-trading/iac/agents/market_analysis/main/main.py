import boto3
import json
import os
import re
import io
import time
from typing import Dict, Any, Optional
from a2a_core import get_logger

logger = get_logger({"agent": "MarketAnalysisAgent"})


def build_prompt(input_data: Dict[str, Any]) -> str:
    sector = input_data.get("sector", "technology sector")
    focus = input_data.get("focus", "overall outlook")
    risk_factors = input_data.get("riskFactors", [])
    summary_length = input_data.get("summaryLength", 150)

    risks = ", ".join(risk_factors) if risk_factors else "market uncertainty"

    prompt = (
        f"You are a financial analyst. Provide a market summary for the {sector}. "
        f"Focus on: {focus}. Discuss key trends, opportunities, and threats. "
        f"Consider risk factors such as: {risks}. Limit your response to approximately {summary_length} words."
    )

    print("Prompt built", {"sector": sector, "focus": focus, "risks": risks})
    return prompt


class MarketAnalysisAgent:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = "us-east-1"):
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client(service_name="bedrock-runtime", region_name=self.region)

    def _invoke_claude_stream(self, prompt: str) -> str:
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
            logger.error("Streaming failed", {"error": str(e)})
            raise e

    def extract_tags(self, summary: str) -> Dict[str, Any]:
        try:
            prompt = (
                f"Analyze the following market summary and return 3–5 key themes as a list of 'tags', and "
                f"the overall sentiment (positive, neutral, or negative). "
                f"Respond with JSON ONLY in the format:\n"
                f"{{\"tags\": [\"tag1\", \"tag2\"], \"sentiment\": \"positive\"}}\n\n"
                f"Summary:\n\"{summary}\""
            )

            messages = [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ]

            response_stream = self.client.converse_stream(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": 200,
                    "temperature": 0.3,
                    "topP": 0.9
                }
            )

            output = io.StringIO()
            for event in response_stream["stream"]:
                if "contentBlockDelta" in event:
                    output.write(event["contentBlockDelta"]["delta"].get("text", ""))

            response_text = output.getvalue().strip()
            print("Tag extraction response received", {"raw": response_text})

            match = re.search(r'\{[\s\S]*?\}', response_text)
            if not match:
                return {"tags": [], "sentiment": "unknown"}

            parsed = json.loads(match.group())
            if isinstance(parsed, str):
                parsed = json.loads(parsed)

            return {
                "tags": parsed.get("tags", []),
                "sentiment": parsed.get("sentiment", "unknown")
            }

        except Exception as e:
            logger.error("Tag extraction failed", {"error": str(e)})
            return {"tags": [], "sentiment": "unknown"}

    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = build_prompt(input_data)
            start = time.time()

            summary = self._invoke_claude_stream(prompt)

            if not summary:
                logger.warning("No summary returned")
                return {
                    "summary": "",
                    "tags": [],
                    "sentiment": "unknown"
                }

            tag_data = self.extract_tags(summary)

            duration = time.time() - start
            print("Market analysis complete", {
                "duration_sec": duration,
                "tags": tag_data.get("tags"),
                "sentiment": tag_data.get("sentiment")
            })

            return {
                "summary": summary,
                "tags": tag_data.get("tags", []),
                "sentiment": tag_data.get("sentiment", "unknown")
            }

        except Exception as e:
            logger.error("Analysis failed", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            return {
                "summary": "",
                "tags": [],
                "sentiment": "unknown"
            }
