from strands import tool
from typing import Dict, Any
from limit_db import CustomerSupportDB

db = CustomerSupportDB()

@tool()
def process_refund(customer_id: str, billing_id: int, action: str, amount: float = None) -> Dict[str, Any]:
    """
    Process refund requests and provide status updates for existing refund requests.

    Args:
        customer_id: The unique identifier for the customer.
        billing_id: The ID of the billing record for which the refund is requested.
        action: The action to perform. Must be either "request" or "status".
        amount: The amount to refund (required for "request" action).

    Returns:
        Dict containing the result of the operation
    """
    try:
        if action not in ["request", "status"]:
            return {"success": False, "message": "Invalid action. Use 'request' or 'status'."}

        if action == "request":
            if amount is None:
                return {"success": False, "message": "Amount is required for refund requests."}
            
            refund_id = db.create_refund_request(customer_id, billing_id, amount)
            return {
                "success": True,
                "message": f"Refund request initiated for billing ID {billing_id}.",
                "refund_info": {
                    "refund_id": refund_id,
                    "customer_id": customer_id,
                    "billing_id": billing_id,
                    "amount": amount,
                    "status": "PROCESSING"
                }
            }
        else:  # status
            refund_status = db.get_refund_status(customer_id, billing_id)
            if refund_status:
                return {
                    "success": True,
                    "message": f"Refund status retrieved for billing ID {billing_id}.",
                    "refund_info": refund_status
                }
            else:
                return {
                    "success": False,
                    "message": f"No refund request found for billing ID {billing_id}."
                }
    except Exception as e:
        return {"success": False, "message": f"Error processing refund action: {str(e)}"}
