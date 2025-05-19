import boto3
import json
import os
import re
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
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client(service_name="bedrock-runtime", region_name=self.region)

    def converse(self, messages: list) -> str:
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "temperature": 0.5,
                    "topP": 0.9
                },
                additionalModelRequestFields={
                    "top_k": 100
                }
            )

            text = response["output"]["message"]["content"][0]["text"]
            return text.strip()

        except Exception as e:
            logger.error("Bedrock converse() failed", {"error": str(e)})
            raise e

    def call_bedrock(self, prompt: str) -> str:
        print("Calling Claude 3 via converse()", {"prompt_preview": prompt[:120]})

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]

        return self.converse(messages)

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

            response_text = self.converse(messages)
            print("Claude raw tag extraction response", {"response": response_text})

            json_match = re.search(r'\{[\s\S]*?\}', response_text)
            if not json_match:
                logger.warning("No valid JSON block found in response")
                return {"tags": [], "sentiment": "unknown"}

            raw_json = json_match.group()

            parsed = json.loads(raw_json)
            if isinstance(parsed, str):
                print("Nested JSON detected, double parsing required")
                parsed = json.loads(parsed)

            if isinstance(parsed, dict) and "tags" in parsed and "sentiment" in parsed:
                return parsed

            logger.warning("Parsed JSON is missing required fields")
            return {"tags": [], "sentiment": "unknown"}

        except Exception as e:
            logger.error("Tag extraction failed", {
                "error": str(e),
                "summary": summary
            })
            return {"tags": [], "sentiment": "unknown"}


    def analyze(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = build_prompt(input_data)
            print("Analysis started", {
                "input": input_data
            })

            summary = self.call_bedrock(prompt)

            if not summary:
                logger.warning("No summary returned from Bedrock")
                return {
                    "summary": "",
                    "tags": [],
                    "sentiment": "unknown"
                }

            tag_data = self.extract_tags(summary)

            print("Analysis completed", {
                "summaryLength": len(summary),
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
