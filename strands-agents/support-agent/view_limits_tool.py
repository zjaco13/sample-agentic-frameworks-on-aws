from typing import Dict, Any
from limit_db import CustomerSupportDB
from strands import tool

# Initialize the database
db = CustomerSupportDB()

@tool()
def view_customer_limits(customer_id: str) -> Dict[str, Any]:
    """
    View all feature limits for a specific customer
    
    Args:
        customer_id: The ID of the customer
    
    Returns:
        Dict containing customer's current limits for all features
    """
    try:
        # Get current limits for the customer
        current_limits = db.get_customer_limits(customer_id)
        
        if not current_limits:
            return {
                "success": False,
                "error": f"No limits found for customer {customer_id}"
            }

        return {
            "success": True,
            "result": {
                "customer_id": customer_id,
                "limits": current_limits
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error retrieving limits for customer: {str(e)}"
        }
