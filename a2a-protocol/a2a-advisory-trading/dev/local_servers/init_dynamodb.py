import boto3
import os
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE_NAME = os.getenv("TRADE_LOG_TABLE", "TradeExecutionLog")

def create_table():
    dynamodb = boto3.client("dynamodb", region_name=REGION)

    existing_tables = dynamodb.list_tables()["TableNames"]
    if TABLE_NAME in existing_tables:
        print(f"Table '{TABLE_NAME}' already exists.")
        return

    print(f"Creating table '{TABLE_NAME}' ...")
    resp = dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": "confirmationId", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "confirmationId", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName=TABLE_NAME)
    print("Table created.")

if __name__ == "__main__":
    create_table()
