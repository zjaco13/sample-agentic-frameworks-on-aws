import os
import re
import json
from typing import Optional
from strands import Agent as StrandsAgent
from strands.models import BedrockModel
from a2a_core import get_logger

logger = get_logger({"agent": "MarketAnalysisAgent"})

SYSTEM_PROMPT = (
    "You are a financial analyst. Provide clear, insightful market summaries. "
    "Answer the questions to the best of your model training data."
)

class MarketAnalysisAgent:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = None):
        model_id = model_id or os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
        region_name = region or os.environ.get("AWS_PRIMARY_REGION", "us-east-1")
        self.model = BedrockModel(
            model_id=model_id,
            streaming=True,
            region_name=region_name,
            max_tokens=600
        )
        self.strands_agent = StrandsAgent(
            model=self.model,
            system_prompt=SYSTEM_PROMPT
        )

    def build_prompt(self, input_data):
        user_context = input_data.get("userContext", None)
        extra_context = input_data.get("extraContext", None)
        sector = input_data.get("sector", "technology sector")
        focus = input_data.get("focus", "overall outlook")
        risk_factors = input_data.get("riskFactors", [])
        summary_length = input_data.get("summaryLength", 150)

        risks = ", ".join(risk_factors) if risk_factors else "market uncertainty"

        prompt = (
            f"Knowing the user request that was initially sent to the portfolio manager: {user_context}. "
            f"Write a concise, coherent, and natural-sounding market summary (about {summary_length} words) for the {sector} sector. "
            f"Focus on {focus}. Discuss key trends, opportunities, and threats in a single paragraph. "
            f"If the user request has the intention of making a trade but did not specify which stock or company, "
            f"then the summary should name out what is the company that matches user description for investment. "
            f"Do NOT include a title, bullet points, or any formatting—write in natural English prose only. "
            f"Consider risk factors such as: {risks}."
        )

        '''
        For local use only
        '''
        # if extra_context:
        #     prompt.__add__(f"Here are some more additional context send by user: {extra_context}. Use this information as part of the analysis.")

        return prompt

    def analyze(self, input_data):
        prompt = self.build_prompt(input_data)
        logger.info("Sending prompt to Strands", {"prompt": prompt[:200]})

        try:
            response = self.strands_agent(prompt)
            summary = str(response)
            logger.info("Strands agent full response", {"response": str(summary)})
            tag_data = self.extract_tags(summary)

            return {
                "summary": summary,
                "tags": tag_data.get("tags", []),
                "sentiment": tag_data.get("sentiment", "unknown")
            }
        except Exception as e:
            logger.error("Strands agent failed", {"error": str(e)})
            return {"summary": "", "tags": [], "sentiment": "unknown"}

    def extract_tags(self, summary):
        prompt = (
            "Analyze the following market summary and return exactly 4-7 key themes as a list of 'tags', "
            "and the overall sentiment (positive, neutral, or negative) for investors. "
            "Respond with nothing except a single JSON object with this format:\n"
            '{"tags": ["tag1", "tag2", "tag3"], "sentiment": "positive"}\n'
            "No title. No explanation. No extra text.\n\n"
            f"Summary:\n\"{summary}\""
        )
        try:
            result = str(self.strands_agent(prompt))

            try:
                parsed = json.loads(result)
                tags = parsed.get("tags", [])
                sentiment = parsed.get("sentiment", "unknown")
                if not isinstance(tags, list):
                    tags = [tags] if tags else []
                if not isinstance(sentiment, str):
                    sentiment = str(sentiment)
                return {"tags": tags, "sentiment": sentiment}
            except Exception as direct_parse_error:
                match = re.search(r'\{[\s\S]*?\}', result)
                if match:
                    raw_json = match.group()
                    try:
                        parsed = json.loads(raw_json)
                        tags = parsed.get("tags", [])
                        sentiment = parsed.get("sentiment", "unknown")
                        if not isinstance(tags, list):
                            tags = [tags] if tags else []
                        if not isinstance(sentiment, str):
                            sentiment = str(sentiment)
                        return {"tags": tags, "sentiment": sentiment}
                    except Exception as e:
                        logger.warning("Failed to parse tags JSON", {"error": str(e), "raw_json": raw_json})
                logger.warning("No JSON found in tag extraction output", {"llm_output": result})
                return {"tags": [], "sentiment": "unknown"}
        except Exception as e:
            logger.error("Tag extraction failed (LLM or parse error)", {"error": str(e)})
            return {"tags": [], "sentiment": "unknown"}
