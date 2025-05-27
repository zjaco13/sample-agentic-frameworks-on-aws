import boto3
import os
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional
from a2a_core import get_logger

logger = get_logger({"agent": "TradeExecutionAgent"})


class TradeExecutionAgent:
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None):
        self.table_name = table_name or os.environ.get("TRADE_LOG_TABLE", "TradeExecutionLog")
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client("dynamodb", region_name=self.region)

    def validate(self, input_data: Dict[str, Any]) -> Optional[str]:
        action = input_data.get("action")
        quantity = input_data.get("quantity")
        symbol = input_data.get("symbol")

        if action not in ["Buy", "Sell", "buy", "sell", "BUY", "SELL"]:
            return "Invalid action. Must be 'Buy' or 'Sell'."
        if not isinstance(quantity, int) or quantity <= 0:
            return "Quantity must be a positive integer."
        if not isinstance(symbol, str) or not symbol:
            return "Symbol must be a non-empty string."
        return None

    def log_trade(self, trade: Dict[str, Any]) -> str:
        confirmation_id = f"TRADE-{uuid.uuid4().hex[:8].upper()}"

        item = {
            "confirmationId": {"S": confirmation_id},
            "timestamp": {"S": datetime.utcnow().isoformat()},
            "action": {"S": trade["action"]},
            "symbol": {"S": trade["symbol"]},
            "quantity": {"N": str(trade["quantity"])},
            "status": {"S": "Executed"}
        }

        self.client.put_item(
            TableName=self.table_name,
            Item=item
        )

        print("Trade logged", {
            "confirmationId": confirmation_id,
            "symbol": trade["symbol"],
            "quantity": trade["quantity"],
            "action": trade["action"]
        })

        return confirmation_id

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        print("Received trade execution request", {"input": input_data})

        error = self.validate(input_data)
        if error:
            logger.warning("Validation failed", {"reason": error})
            return {
                "status": "rejected",
                "reason": error
            }

        confirmation = self.log_trade(input_data)

        duration = time.time() - start
        print("Trade execution complete", {"duration_sec": duration})

        return {
            "status": "executed",
            "confirmationId": confirmation
        }
