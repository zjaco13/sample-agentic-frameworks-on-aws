import ast
import os
import sqlite3
import requests
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

from langchain_community.utilities.sql_database import SQLDatabase

load_dotenv()


# ------------------------------------------------------------
# LLM Initialization
# ------------------------------------------------------------
# NOTE: AWS Bedrock has a known incompatibility with LangChain's create_agent tool calling.
# See docs/BEDROCK_LIMITATION.md for details. Using OpenAI for reliable tool calling support.

from langchain_openai import ChatOpenAI

model = os.getenv("OPENAI_MODEL", "gpt-4o")
print(f"Initializing OpenAI: {model}")

llm = ChatOpenAI(
    model=model,
    temperature=0
)
# llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", temperature=0)
# llm = ChatVertexAI(model_name="gemini-1.5-flash-002", temperature=0)
# ------------------------------------------------------------
# Database Utilities
# ------------------------------------------------------------
def get_engine_for_chinook_db():
    """Pull sql file, populate in-memory database, and create engine."""
    url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
    response = requests.get(url)
    sql_script = response.text

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.executescript(sql_script)
    return create_engine(
        "sqlite://",
        creator=lambda: connection,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

engine = get_engine_for_chinook_db()
db = SQLDatabase(engine)

# ------------------------------------------------------------
# Node Helper Functions
# ------------------------------------------------------------
def get_customer_id_from_identifier(identifier: str) -> Optional[int]:
    """
    Retrieve Customer ID using an identifier, which can be a customer ID, email, or phone number.
    Args:
        identifier (str): The identifier can be customer ID, email, or phone.
    Returns:
        Optional[int]: The CustomerId if found, otherwise None.
    """
    if identifier.isdigit():
        return int(identifier)
    elif identifier[0] == "+":
        query = f"SELECT CustomerId FROM Customer WHERE Phone = '{identifier}';"
        result = db.run(query)
        formatted_result = ast.literal_eval(result)
        if formatted_result:
            return formatted_result[0][0]
    elif "@" in identifier:
        query = f"SELECT CustomerId FROM Customer WHERE Email = '{identifier}';"
        result = db.run(query)
        formatted_result = ast.literal_eval(result)
        if formatted_result:
            return formatted_result[0][0]
    return None 

def format_user_memory(user_data):
    """
    Formats customer preferences from memory for use in agent context.

    Args:
        user_data: Dictionary containing 'memory' key with customer profile

    Returns:
        str: Formatted string of customer preferences
    """
    profile = user_data['memory']
    result_parts = []

    # Music preferences
    if hasattr(profile, 'music_preferences') and profile.music_preferences:
        result_parts.append(f"Music Preferences: {', '.join(profile.music_preferences)}")

    # Favorite colors
    if hasattr(profile, 'favorite_colors') and profile.favorite_colors:
        result_parts.append(f"Favorite Colors: {', '.join(profile.favorite_colors)}")

    # Dress/clothing size
    if hasattr(profile, 'dress_size') and profile.dress_size:
        result_parts.append(f"Dress Size: {profile.dress_size}")

    # Shoe size
    if hasattr(profile, 'shoe_size') and profile.shoe_size:
        result_parts.append(f"Shoe Size: {profile.shoe_size}")

    # Style preferences
    if hasattr(profile, 'style_preferences') and profile.style_preferences:
        result_parts.append(f"Style Preferences: {', '.join(profile.style_preferences)}")

    # General interests
    if hasattr(profile, 'interests') and profile.interests:
        result_parts.append(f"Interests: {', '.join(profile.interests)}")

    result = "\n".join(result_parts)
    return result.strip() if result else "No preferences stored yet"