import os
import re
import json
import time
from typing import Optional
from strands import Agent as StrandsAgent
from strands.models import BedrockModel
from a2a_core import get_logger

logger = get_logger({"agent": "RiskAssessmentAgent"})

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
            system_prompt="You are a financial risk analyst. Provide clear, factual, and structured JSON risk assessments only in the requested format."
        )

    def build_prompt(self, input_data):
        user_context = input_data.get("userContext", None)
        extra_context = input_data.get("extraContext", None)
        analysis_type = input_data.get("analysisType", "general")
        sector = input_data.get("sector", "UNKNOWN_SECTOR")
        time_horizon = input_data.get("timeHorizon", "medium")
        capital_exposure = input_data.get("capitalExposure", "moderate")
        specific_asset = input_data.get("specificAsset", {})

        if analysis_type == "asset" and specific_asset:
            symbol = specific_asset.get("symbol", "UNKNOWN")
            quantity = specific_asset.get("quantity", "TBD")
            action = specific_asset.get("action", "buy")
            prompt = (
                f"Knowing the following user input to portfolio manager as the context: {user_context}. "
                f"Evaluate the risk of {action}ing {quantity} shares of {symbol} in the {sector} sector "
                f"with a {time_horizon} time horizon (where time horizon can be 'short' (up to 3 months), 'medium' (3-12 months), "
                f"'long' (over 1 year), or a specific period like 'next 18 months', 'Q4 2025', etc.) "
                f"and {capital_exposure} capital exposure.\n"
                f"Your assessment MUST explicitly mention sector- and asset-specific factors, as well as the user profile if they provided any information, and must not answer in generic terms.\n"
                f"Respond ONLY with a single JSON object, with the following format:\n"
                f"{{\"score\": <0-100>, \"rating\": \"High|Moderate|Low\", \"factors\": [\"<factor1>\", \"<factor2>\"], \"explanation\": \"One short paragraph explaining the rating and referencing concrete market/sector/asset facts.\"}}\n"
                f"Do NOT mention any other sector or asset.\n"
                f"\nExample: {{\"score\": 72, \"rating\": \"Moderate\", \"factors\": [\"regulatory uncertainty\", \"low trading volume\"], \"explanation\": \"Tesla faces moderate risk due to upcoming regulatory changes in EV markets and recent reductions in sales volume.\"}}\n"
            )

        elif analysis_type == "sector" and sector:
            prompt = (
                f"Knowing the following user input to portfolio manager as the context: {user_context}. "
                f"Evaluate the CURRENT risk profile for the {sector} sector for investors, "
                f"with a {time_horizon} time horizon (can be 'short' (up to 3 months), 'medium' (3-12 months), "
                f"'long' (over 1 year), or specific periods like 'next 18 months', 'Q4 2025', etc.) "
                f"and {capital_exposure} capital exposure.\n"
                f"Base your analysis only on factors and trends relevant to the {sector} sector.\n"
                f"Your assessment MUST explicitly mention sector- and asset-specific factors, as well as the user profile in relation to investment in the sector if they provided any information, and must not answer in generic terms.\n"
                f"Respond ONLY with a JSON object like this:\n"
                f"{{\"score\": <0-100>, \"rating\": \"High|Moderate|Low\", \"factors\": [\"<factor1>\", \"<factor2>\"], \"explanation\": \"Short sector-specific risk summary.\"}}\n"
                f"Do NOT answer in generic terms—make sure your explanation is about {sector} only.\n"
                f"\nExample: {{\"score\": 80, \"rating\": \"High\", \"factors\": [\"patent cliffs\", \"regulatory risk\"], \"explanation\": \"Healthcare faces high risk due to upcoming patent expirations and regulatory changes impacting drug approvals.\"}}\n"
            )
        else:
            prompt = (
                f"Knowing the following user input to portfolio manager as the context: {user_context}. "
                f"Provide a general market risk assessment with a {time_horizon} time horizon "
                f"(can be 'short' (up to 3 months), 'medium' (3-12 months), 'long' (over 1 year), "
                f"or specific periods like 'next 18 months', 'Q4 2025', etc.) "
                f"and {capital_exposure} capital exposure.\n"
                f"Your assessment MUST explicitly mention sector- and asset-specific factors, as well as the user profile in relation to investment in the sector if they provided any information, and must not answer in generic terms.\n"
                f"Respond ONLY with a JSON object like this:\n"
                f"{{\"score\": <0-100>, \"rating\": \"High|Moderate|Low\", \"factors\": [\"<factor1>\", \"<factor2>\"], \"explanation\": \"Short summary of current market-wide risk drivers.\"}}\n"
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
        # if extra_context:
        #     prompt.__add__(f"Here are some more additional context send by user: {extra_context}. Use this information as part of the analysis.")

        return prompt

    def analyze(self, input_data):
        try:
            prompt = self.build_prompt(input_data)
            start = time.time()
            logger.info("Sending prompt to Strands", {"prompt": prompt[:200]})

            result = str(self.strands_agent(prompt)).strip()
            logger.info("Strands agent full response", {"response": result})

            try:
                parsed = json.loads(result)
            except Exception:
                match = re.search(r'\{[\s\S]*?\}', result)
                if match:
                    parsed = json.loads(match.group())
                else:
                    logger.warning("No JSON block found in risk response", {"output": result})
                    parsed = {}

            output = {
                "score": parsed.get("score", -1),
                "rating": parsed.get("rating", "Unknown"),
                "factors": parsed.get("factors", []),
                "explanation": parsed.get("explanation", "")
            }
            duration = time.time() - start
            logger.info("Risk analysis complete", {
                "duration_sec": duration,
                "analysis_type": input_data.get("analysisType", "general"),
                "score": output.get("score"),
                "rating": output.get("rating"),
                "factors": output.get("factors"),
                "explanation": output.get("explanation")
            })
            return output

        except Exception as e:
            logger.error("Risk analysis failed", {"error": str(e)})
            return {
                "score": -1,
                "rating": "Unknown",
                "factors": [],
                "explanation": str(e)
            }
