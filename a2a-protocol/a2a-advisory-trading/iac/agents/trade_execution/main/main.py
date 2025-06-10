import boto3
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from a2a_core import get_logger
from a2a.types import Task, Message, Part, Role, TaskState, TaskStatus

logger = get_logger({"agent": "TradeExecutionAgent"})

class TradeExecutionAgent:
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None):
        self.table_name = table_name or os.environ.get("TRADE_LOG_TABLE", "TradeExecutionLog")
        self.region = region or os.environ.get("AWS_PRIMARY_REGION", "us-east-1")
        self.client = boto3.client("dynamodb", region_name=self.region)

    def extract_user_input_from_task(self, task: Task) -> Dict[str, Any]:
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
                data = part.root.data
                _input_data["action"] = data.get("action", "").lower()
                _input_data["quantity"] = int(data.get("quantity", 0))
                _input_data["symbol"] = data.get("symbol", "")

        print(f"DEBUG: Extracted data: {_input_data}")
        return _input_data

    def validate(self, input_data: Dict[str, Any]) -> Optional[str]:

        action = input_data.get("action")
        quantity = input_data.get("quantity")
        symbol = input_data.get("symbol")

        if not action or action.lower() not in ["buy", "sell"]:
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
            "quantity": {"N": str(trade["quantity"])}
        }

        try:
            self.client.put_item(
                TableName=self.table_name,
                Item=item
            )
            return confirmation_id
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
            raise

    def execute_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:

        confirmation_id = self.log_trade(trade_data)

        return {
            "status": "executed",
            "confirmationId": confirmation_id,
            "action": trade_data["action"],
            "symbol": trade_data["symbol"],
            "quantity": trade_data["quantity"],
            "timestamp": datetime.utcnow().isoformat()
        }

    def analyze(self, task: Task) -> Task:
        try:
            input_data = self.extract_user_input_from_task(task)

            print("Input data: ", input_data)

            validation_error = self.validate(input_data)
            if validation_error:
                return self.create_error_response(task, validation_error)

            print("Validation error: ", validation_error)

            result = self.execute_trade(input_data)

            print("Result: ", result)

            response_text = (
                f"Trade executed successfully:\n"
                f"- Action: {result['action'].upper()}\n"
                f"- Symbol: {result['symbol']}\n"
                f"- Quantity: {result['quantity']}\n"
                f"- Confirmation ID: {result['confirmationId']}\n"
                f"- Timestamp: {result['timestamp']}"
            )

            print("Response text: ", response_text)

            task.status = TaskStatus(
                state=TaskState.completed,
                message=Message(
                    role=Role.agent,
                    parts=[Part(kind="text", text=response_text)],
                    messageId=str(uuid.uuid4()),
                    taskId=task.id,
                    contextId=task.contextId
                )
            )

        except Exception as e:
            logger.error(f"Error processing trade execution: {e}")
            return self.create_error_response(task, str(e))

        print("Task: ", task)

        return task

    def create_error_response(self, task: Task, error_message: str) -> Task:
        task.status = TaskStatus(
            state=TaskState.failed,
            message=Message(
                role=Role.agent,
                parts=[Part(kind="text", text=f"Error: {error_message}")],
                messageId=str(uuid.uuid4()),
                taskId=task.id,
                contextId=task.contextId
            )
        )
        return task