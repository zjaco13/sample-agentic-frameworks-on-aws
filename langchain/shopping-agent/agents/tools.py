from langchain.tools import tool, ToolRuntime
from agents.utils import db

# ------------------------------------------------------------
# Opensearch E-commerce Agent Tools
# ------------------------------------------------------------
import os
from agents.opensearch_client import get_opensearch_client

@tool
def search_products_by_query(runtime: ToolRuntime, query: str, max_results: int = 10) -> list[dict]:
    """
    Search the product catalog using semantic/neural search via OpenSearch.
    Returns product details matching the customer's query using AI-powered semantic understanding.

    Args:
        query: Natural language search query (e.g., "comfortable hiking backpack")
        max_results: Maximum number of products to return (default: 10)

    Returns:
        list[dict]: List of matching products with relevance scores
    """
    client = get_opensearch_client()
    model_id = os.getenv('OPENSEARCH_MODEL_ID')
    index_name = os.getenv('OPENSEARCH_INDEX_PRODUCTS', 'shopping_products')

    # Perform neural search using the deployed ML model
    search_body = {
        "size": max_results,
        "query": {
            "neural": {
                "product_vector": {
                    "query_text": query,
                    "model_id": model_id,
                    "k": max_results * 2  # Get more candidates for better ranking
                }
            }
        },
        "_source": {
            "excludes": ["product_vector"]  # Don't return the vector in results
        }
    }

    try:
        response = client.search(index=index_name, body=search_body)

        products = []
        for hit in response['hits']['hits']:
            product = hit['_source']
            product['relevance_score'] = round(hit['_score'], 2)
            products.append(product)

        return products
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


@tool
def filter_products_by_category_and_price(
    runtime: ToolRuntime,
    category: str = None,
    min_price: float = 0,
    max_price: float = 10000,
    promoted_only: bool = False,
    max_results: int = 20
) -> list[dict]:
    """
    Filter and browse products by category, price range, and promotion status.
    Use this for structured browsing when customers want to see products in a specific category or price range.

    Args:
        category: Product category to filter by (e.g., "accessories", "electronics", "apparel")
        min_price: Minimum price in dollars (default: 0)
        max_price: Maximum price in dollars (default: 10000)
        promoted_only: Only return promoted/featured products (default: False)
        max_results: Maximum number of products to return (default: 20)

    Returns:
        list[dict]: List of products matching the filters
    """
    client = get_opensearch_client()
    index_name = os.getenv('OPENSEARCH_INDEX_PRODUCTS', 'shopping_products')

    # Build filter query
    filters = []

    if category:
        filters.append({"term": {"category": category.lower()}})

    filters.append({"range": {"price": {"gte": min_price, "lte": max_price}}})
    filters.append({"range": {"current_stock": {"gt": 0}}})  # Only in-stock items

    if promoted_only:
        filters.append({"term": {"promoted": True}})

    search_body = {
        "size": max_results,
        "query": {
            "bool": {
                "filter": filters
            }
        },
        "sort": [
            {"promoted": {"order": "desc"}},  # Promoted items first
            {"price": {"order": "asc"}}       # Then by price ascending
        ],
        "_source": {
            "excludes": ["product_vector"]
        }
    }

    try:
        response = client.search(index=index_name, body=search_body)

        products = []
        for hit in response['hits']['hits']:
            products.append(hit['_source'])

        return products
    except Exception as e:
        return [{"error": f"Filter failed: {str(e)}"}]


@tool
def get_product_recommendations(runtime: ToolRuntime, max_results: int = 5) -> list[dict]:
    """
    Get personalized product recommendations based on customer's preferences from their memory profile.
    Uses hybrid search combining neural semantic search with keyword matching for best results.

    Args:
        max_results: Maximum number of recommendations (default: 5)

    Returns:
        list[dict]: List of recommended products with relevance scores
    """
    loaded_memory = runtime.state.get("loaded_memory", "")

    client = get_opensearch_client()
    model_id = os.getenv('OPENSEARCH_MODEL_ID')
    index_name = os.getenv('OPENSEARCH_INDEX_PRODUCTS', 'shopping_products')

    # If no preferences, return promoted products
    if not loaded_memory or loaded_memory.strip() == "":
        return filter_products_by_category_and_price.invoke(
            {"runtime": runtime, "promoted_only": True, "max_results": max_results}
        )

    # Hybrid search: Neural + BM25 for better relevance
    search_body = {
        "size": max_results,
        "query": {
            "bool": {
                "should": [
                    {
                        "neural": {
                            "product_vector": {
                                "query_text": loaded_memory,
                                "model_id": model_id,
                                "k": max_results * 3
                            }
                        }
                    },
                    {
                        "multi_match": {
                            "query": loaded_memory,
                            "fields": ["name^2", "description", "category"],
                            "type": "best_fields",
                            "boost": 0.5  # Neural search gets more weight
                        }
                    }
                ],
                "filter": [
                    {"range": {"current_stock": {"gt": 0}}}
                ],
                "minimum_should_match": 1
            }
        },
        "_source": {
            "excludes": ["product_vector"]
        }
    }

    try:
        response = client.search(index=index_name, body=search_body)

        products = []
        for hit in response['hits']['hits']:
            product = hit['_source']
            product['relevance_score'] = round(hit['_score'], 2)
            products.append(product)

        return products
    except Exception as e:
        return [{"error": f"Recommendations failed: {str(e)}"}]


@tool
def get_product_by_id(runtime: ToolRuntime, product_id: str) -> dict:
    """
    Get detailed information about a specific product by its ID.
    Use this when you need to look up a specific product that was mentioned or referenced.

    Args:
        product_id: The unique product identifier

    Returns:
        dict: Product details or error message
    """
    client = get_opensearch_client()
    index_name = os.getenv('OPENSEARCH_INDEX_PRODUCTS', 'shopping_products')

    try:
        response = client.get(
            index=index_name,
            id=product_id,
            _source_excludes=["product_vector"]
        )
        return response['_source']
    except Exception as e:
        return {"error": f"Product {product_id} not found: {str(e)}"}


# Export OpenSearch tools
opensearch_tools = [
    search_products_by_query,
    filter_products_by_category_and_price,
    get_product_recommendations,
    get_product_by_id
]

# ------------------------------------------------------------
# Invoice Subagent Tools
# ------------------------------------------------------------
@tool 
def get_invoices_by_customer_sorted_by_date(runtime: ToolRuntime) -> list[dict]:
    """
    Look up all invoices for a customer using their ID, the customer ID is in a state variable, so you will not see it in the message history.
    The invoices are sorted in descending order by invoice date, which helps when the customer wants to view their most recent/oldest invoice, or if 
    they want to view invoices within a specific date range.
    
    Returns:
        list[dict]: A list of invoices for the customer.
    """
    # customer_id = state.get("customer_id", "Unknown user")
    customer_id = runtime.state.get("customer_id", {})
    return db.run(f"SELECT * FROM Invoice WHERE CustomerId = {customer_id} ORDER BY InvoiceDate DESC;")


@tool 
def get_invoices_sorted_by_unit_price(runtime: ToolRuntime) -> list[dict]:
    """
    Use this tool when the customer wants to know the details of one of their invoices based on the unit price/cost of the invoice.
    This tool looks up all invoices for a customer, and sorts the unit price from highest to lowest. In order to find the invoice associated with the customer, 
    we need to know the customer ID. The customer ID is in a state variable, so you will not see it in the message history.

    Returns:
        list[dict]: A list of invoices sorted by unit price.
    """
    # customer_id = state.get("customer_id", "Unknown user")
    query = f"""
        SELECT Invoice.*, InvoiceLine.UnitPrice
        FROM Invoice
        JOIN InvoiceLine ON Invoice.InvoiceId = InvoiceLine.InvoiceId
        WHERE Invoice.CustomerId = {customer_id}
        ORDER BY InvoiceLine.UnitPrice DESC;
    """
    customer_id = runtime.state.get("customer_id", {})
    return db.run(query)


@tool
def get_employee_by_invoice_and_customer(runtime: ToolRuntime, invoice_id: int) -> dict:
    """
    This tool will take in an invoice ID and a customer ID and return the employee information associated with the invoice.
    The customer ID is in a state variable, so you will not see it in the message history.
    Args:
        invoice_id (int): The ID of the specific invoice.

    Returns:
        dict: Information about the employee associated with the invoice.
    """
    # customer_id = state.get("customer_id", "Unknown user")
    customer_id = runtime.state.get("customer_id", {})
    query = f"""
        SELECT Employee.FirstName, Employee.Title, Employee.Email
        FROM Employee
        JOIN Customer ON Customer.SupportRepId = Employee.EmployeeId
        JOIN Invoice ON Invoice.CustomerId = Customer.CustomerId
        WHERE Invoice.InvoiceId = ({invoice_id}) AND Invoice.CustomerId = ({customer_id});
    """
    
    employee_info = db.run(query, include_columns=True)
    
    if not employee_info:
        return f"No employee found for invoice ID {invoice_id} and customer identifier {customer_id}."
    return employee_info

invoice_tools = [get_invoices_by_customer_sorted_by_date, get_invoices_sorted_by_unit_price, get_employee_by_invoice_and_customer]

