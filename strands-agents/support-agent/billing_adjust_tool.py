from typing import Dict, Any
from limit_db import CustomerSupportDB
from strands import tool

db = CustomerSupportDB()

@tool()
def adjust_billing(billing_id: int, new_amount: float) -> Dict[str, Any]:
    """
    Adjust the billing amount for a specific invoice
    
    Args:
        billing_id: The ID of the billing record to adjust
        new_amount: The new amount for the invoice
    
    Returns:
        Dict containing the result of the operation
    """
    try:
        success = db.adjust_billing(billing_id, new_amount)
        if success:
            return {
                "success": True,
                "result": f"Billing amount for ID {billing_id} adjusted to ${new_amount:.2f}"
            }
        else:
            return {
                "success": False,
                "error": f"Billing record with ID {billing_id} not found"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error adjusting billing: {str(e)}"
        }
