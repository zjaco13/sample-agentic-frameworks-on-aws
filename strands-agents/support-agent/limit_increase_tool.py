from typing import Dict, Any
from limit_db import CustomerSupportDB
from strands import tool

# Initialize the database
db = CustomerSupportDB()

@tool()
def increase_limit(customer_id: str, feature_id: str, requested_limit: int) -> Dict[str, Any]:
    """
    Increase the limit for a customer's feature
    
    Args:
        customer_id: The ID of the customer
        feature_id: The ID of the feature to increase limit for
        requested_limit: The new limit value requested
    
    Returns:
        Dict containing the result of the operation
    """
    try:
        # Get current limits for validation
        current_limits = db.get_customer_limits(customer_id)
        
        if not current_limits:
            return {
                "success": False,
                "error": f"No existing limits found for customer {customer_id}"
            }

        # Find the specific feature limit
        current_feature_limit = next((limit for limit in current_limits if limit['feature_id'] == feature_id), None)

        if not current_feature_limit:
            return {
                "success": False,
                "error": f"Feature {feature_id} not found for customer {customer_id}"
            }

        # Validate requested limit
        if requested_limit <= current_feature_limit['current_limit']:
            return {
                "success": False,
                "error": f"Requested limit ({requested_limit}) must be greater than current limit ({current_feature_limit['current_limit']})"
            }

        # Add new limit request
        db.add_limit_request(customer_id, feature_id, requested_limit)

        return {
            "success": True,
            "result": {
                "customer_id": customer_id,
                "feature_id": feature_id,
                "feature_name": current_feature_limit['feature_name'],
                "previous_limit": current_feature_limit['current_limit'],
                "requested_limit": requested_limit,
                "status": "PENDING"
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error processing limit increase request: {str(e)}"
        }
