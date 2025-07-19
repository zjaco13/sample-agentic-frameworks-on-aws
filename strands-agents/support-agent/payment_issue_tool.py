from strands import tool
from typing import Dict, Any
from limit_db import CustomerSupportDB

db = CustomerSupportDB()

@tool()
def resolve_payment_issue(customer_id: str, action: str, card_number: str = None, expiry_date: str = None, cvv: str = None) -> Dict[str, Any]:
    """
    Resolve payment-related issues for a customer's account.

    Args:
        customer_id: The unique identifier for the customer
        action: The action to perform ("update_card" or "add_method")
        card_number: The new credit card number (required for update_card)
        expiry_date: The card expiry date in MM/YY format (required for update_card)
        cvv: The card CVV (required for update_card)

    Returns:
        Dict containing the result of the operation
    """
    try:
        if action not in ["update_card", "add_method"]:
            return {
                "success": False,
                "message": "Invalid action. Use 'update_card' or 'add_method'."
            }

        if action == "update_card":
            if not all([card_number, expiry_date, cvv]):
                return {
                    "success": False,
                    "message": "Card number, expiry date, and CVV are required for updating card."
                }

            # Format the payment information
            new_payment_info = {
                "method": "Credit Card",
                "last_four": card_number[-4:],
                "card_details": {
                    "number": card_number,
                    "expiry": expiry_date,
                    "cvv": cvv
                }
            }

            # Update the payment method in the database
            success = db.update_payment_method(customer_id, new_payment_info)
            
            if success:
                return {
                    "success": True,
                    "message": f"Successfully updated credit card for customer {customer_id}.",
                    "updated_info": {
                        "customer_id": customer_id,
                        "payment_method": f"Credit Card ending in {new_payment_info['last_four']}",
                        "expiry_date": expiry_date
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to update credit card for customer {customer_id}."
                }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error resolving payment issue: {str(e)}"
        }
