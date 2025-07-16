from strands.tools import tool
from typing import Dict, Any
from limit_db import CustomerSupportDB

db = CustomerSupportDB()

@tool()
def manage_customer_feedback(customer_id: str, service: str, rating: int, comment: str = None) -> Dict[str, Any]:
    """
    Collect and manage customer feedback for various services.

    Args:
        customer_id: The unique identifier for the customer.
        service: The service being rated (e.g., "Compute", "Storage", "Database").
        rating: The numerical rating given by the customer (typically 1-5).
        comment: Any additional comments provided by the customer.

    Returns:
        Dict containing the result of the operation
    """
    try:
        if not 1 <= rating <= 5:
            return {"success": False, "message": "Rating must be between 1 and 5."}

        feedback_id = db.add_customer_feedback(customer_id, service, rating, comment)
        
        return {
            "success": True,
            "message": f"Feedback successfully recorded for {service} service.",
            "feedback_info": {
                "feedback_id": feedback_id,
                "customer_id": customer_id,
                "service": service,
                "rating": rating,
                "comment": comment
            }
        }
    except Exception as e:
        return {"success": False, "message": f"Error recording feedback: {str(e)}"}
