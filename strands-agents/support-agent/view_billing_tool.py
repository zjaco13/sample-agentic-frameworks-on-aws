from typing import Dict, Any
from limit_db import CustomerSupportDB
from strands import tool

db = CustomerSupportDB()

@tool()
def view_customer_billing(customer_id: str) -> Dict[str, Any]:
    """
    View billing records for a specific customer
    
    Args:
        customer_id: The ID of the customer
    
    Returns:
        Dict containing customer's billing records
    """
    try:
        billing_records = db.get_customer_billing(customer_id)
        if billing_records:
            return {
                "success": True,
                "result": {
                    "customer_id": customer_id,
                    "billing_records": billing_records
                }
            }
        else:
            return {
                "success": False,
                "error": f"No billing records found for customer {customer_id}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error retrieving billing records: {str(e)}"
        }
