import sqlite3
import json
import pandas as pd
import os
from typing import List, Dict, Any

class CustomerSupportDB:
    def __init__(self, db_path: str = 'customer_support.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def reset_database(self):
        """Remove existing database and create a new one"""
        try:
            # Close any existing connections
            if self.conn:
                self.disconnect()
            
            # Remove the existing database file
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                print(f"Existing database removed: {self.db_path}")
            
            # Create new database and tables
            self.create_tables()
            print("New database created with fresh tables")
            
            return True
        except Exception as e:
            print(f"Error resetting database: {str(e)}")
            return False

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def disconnect(self):
        if self.conn:
            self.conn.close()

    def verify_database(self):
        """
        Verify all tables and their contents in the database
        Returns a summary of the data in each table
        """
        self.connect()
        try:
            summary = {
                "limits": self.count_and_sample("limit_management"),
                "billing": self.count_and_sample("billing"),
                "refunds": self.count_and_sample("refund_requests"),
                "feedback": self.count_and_sample("customer_feedback")
            }
            self.disconnect()
            return summary
        except Exception as e:
            print(f"Error verifying database: {str(e)}")
            self.disconnect()
            return None

    def count_and_sample(self, table_name: str) -> Dict[str, Any]:
        """
        Get count and sample record from a table
        """
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        sample_query = f"SELECT * FROM {table_name} LIMIT 1"
        
        count = pd.read_sql_query(count_query, self.conn).iloc[0,0]
        sample = pd.read_sql_query(sample_query, self.conn).to_dict('records')[0] if count > 0 else None
        
        return {
            "record_count": count,
            "sample_record": sample
        }

    def print_all_data(self):
        """
        Print all data from all tables in a formatted way
        """
        self.connect()
        try:
            # Print Limits
            print("\n=== Limit Management Records ===")
            limits_df = pd.read_sql_query("SELECT * FROM limit_management", self.conn)
            print(limits_df)
    
            # Print Billing
            print("\n=== Billing Records ===")
            billing_df = pd.read_sql_query("SELECT * FROM billing", self.conn)
            print(billing_df)
    
            # Print Refunds
            print("\n=== Refund Requests ===")
            refunds_df = pd.read_sql_query("SELECT * FROM refund_requests", self.conn)
            print(refunds_df)
    
            # Print Feedback
            print("\n=== Customer Feedback ===")
            feedback_df = pd.read_sql_query("SELECT * FROM customer_feedback", self.conn)
            print(feedback_df)
    
        except Exception as e:
            print(f"Error printing data: {str(e)}")
        finally:
            self.disconnect()

    
    def create_tables(self):
        self.connect()
        try:
            # Drop existing tables if they exist
            self.cursor.execute("DROP TABLE IF EXISTS limit_management")
            self.cursor.execute("DROP TABLE IF EXISTS billing")
            self.cursor.execute("DROP TABLE IF EXISTS refund_requests")
            self.cursor.execute("DROP TABLE IF EXISTS customer_feedback")

            # Create tables with explicit column types
            self.cursor.execute('''
            CREATE TABLE limit_management (
                request_id INTEGER PRIMARY KEY,
                customer_id TEXT,
                feature_id TEXT,
                feature_name TEXT,
                default_limit INTEGER,
                current_limit INTEGER,
                requested_limit INTEGER,
                status TEXT,
                request_date TIMESTAMP,
                last_updated TIMESTAMP
            )
            ''')

            self.cursor.execute('''
            CREATE TABLE billing (
                billing_id INTEGER PRIMARY KEY,
                customer_id TEXT,
                invoice_date DATE,
                amount DECIMAL(10, 2),
                status TEXT,
                payment_method TEXT,
                last_four TEXT
            )
            ''')

            self.cursor.execute('''
            CREATE TABLE refund_requests (
                refund_id INTEGER PRIMARY KEY,
                customer_id TEXT,
                billing_id INTEGER,
                request_date DATE,
                amount DECIMAL(10, 2),
                status TEXT
            )
            ''')

            self.cursor.execute('''
            CREATE TABLE customer_feedback (
                feedback_id INTEGER PRIMARY KEY,
                customer_id TEXT,
                service TEXT,
                rating INTEGER,
                comment TEXT,
                date DATE
            )
            ''')

            self.conn.commit()
            print("Tables created successfully!")
        except Exception as e:
            print(f"Error creating tables: {str(e)}")
        finally:
            self.disconnect()

    def import_json_data(self, json_file: str):
        self.connect()
        
        try:
            with open(json_file, 'r') as file:
                data = json.load(file)
            
            # Import limit data if present
            if 'limit_requests' in data:
                df_limits = pd.DataFrame(data['limit_requests'])
                df_limits.to_sql('limit_management', self.conn, if_exists='replace', index=False)
            
            # Import billing data
            if 'billing_records' in data:
                df_billing = pd.DataFrame(data['billing_records'])
                # Ensure billing_id is integer
                df_billing['billing_id'] = df_billing['billing_id'].astype(int)
                df_billing.to_sql('billing', self.conn, if_exists='replace', index=False)
            
            # Import refund requests
            if 'refund_requests' in data:
                df_refunds = pd.DataFrame(data['refund_requests'])
                # Ensure refund_id is integer
                df_refunds['refund_id'] = df_refunds['refund_id'].astype(int)
                df_refunds.to_sql('refund_requests', self.conn, if_exists='replace', index=False)
            
            # Import customer feedback
            if 'customer_feedback' in data:
                df_feedback = pd.DataFrame(data['customer_feedback'])
                # Ensure feedback_id is integer
                df_feedback['feedback_id'] = df_feedback['feedback_id'].astype(int)
                df_feedback.to_sql('customer_feedback', self.conn, if_exists='replace', index=False)
            
            self.conn.commit()
            print("Data imported successfully!")

        except Exception as e:
            print(f"Error importing data: {str(e)}")
        finally:
            self.disconnect()

    def get_all_limits(self) -> List[Dict[str, Any]]:
        self.connect()
        df = pd.read_sql_query("SELECT * FROM limit_management", self.conn)
        self.disconnect()
        return df.to_dict('records')

    def get_customer_limits(self, customer_id: str) -> List[Dict[str, Any]]:
        self.connect()
        df = pd.read_sql_query("SELECT * FROM limit_management WHERE customer_id = ?", 
                               self.conn, params=(customer_id,))
        self.disconnect()
        return df.to_dict('records')

    def add_limit_request(self, customer_id: str, feature_id: str, requested_limit: int):
        self.connect()
        self.cursor.execute("""
            INSERT INTO limit_management 
            (customer_id, feature_id, requested_limit, status, request_date, last_updated)
            VALUES (?, ?, ?, 'PENDING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (customer_id, feature_id, requested_limit))
        self.conn.commit()
        self.disconnect()

    def get_customer_billing(self, customer_id: str) -> List[Dict[str, Any]]:
        self.connect()
        df = pd.read_sql_query("SELECT * FROM billing WHERE customer_id = ?", 
                               self.conn, params=(customer_id,))
        self.disconnect()
        return df.to_dict('records')

    def adjust_billing(self, billing_id: int, new_amount: float) -> bool:
        self.connect()
        self.cursor.execute("""
            UPDATE billing SET amount = ? WHERE billing_id = ?
        """, (new_amount, billing_id))
        rows_affected = self.cursor.rowcount
        self.conn.commit()
        self.disconnect()
        return rows_affected > 0

    def update_payment_method(self, customer_id: str, new_payment_info: Dict[str, Any]) -> bool:
        self.connect()
        self.cursor.execute("""
            UPDATE billing SET payment_method = ?, last_four = ?
            WHERE customer_id = ? AND billing_id = (
                SELECT MAX(billing_id) FROM billing WHERE customer_id = ?
            )
        """, (new_payment_info['method'], new_payment_info['last_four'], customer_id, customer_id))
        rows_affected = self.cursor.rowcount
        self.conn.commit()
        self.disconnect()
        return rows_affected > 0

    # Methods for handling refunds
    def create_refund_request(self, customer_id: str, billing_id: int, amount: float) -> int:
        self.connect()
        try:
            # Get the next refund_id
            self.cursor.execute("SELECT MAX(refund_id) FROM refund_requests")
            max_id = self.cursor.fetchone()[0]
            next_id = 1 if max_id is None else max_id + 1

            self.cursor.execute("""
                INSERT INTO refund_requests 
                (refund_id, customer_id, billing_id, request_date, amount, status)
                VALUES (?, ?, ?, DATE('now'), ?, 'PROCESSING')
            """, (next_id, customer_id, billing_id, amount))
            
            self.conn.commit()
            return next_id
        except Exception as e:
            print(f"Error creating refund request: {str(e)}")
            return None
        finally:
            self.disconnect()

    def get_refund_status(self, customer_id: str, billing_id: int) -> Dict[str, Any]:
        self.connect()
        self.cursor.execute("""
            SELECT * FROM refund_requests
            WHERE customer_id = ? AND billing_id = ?
            ORDER BY request_date DESC LIMIT 1
        """, (customer_id, billing_id))
        result = self.cursor.fetchone()
        self.disconnect()
        if result:
            return dict(zip([column[0] for column in self.cursor.description], result))
        return None

    # Methods for handling feedback
    def add_customer_feedback(self, customer_id: str, service: str, rating: int, comment: str) -> int:
        self.connect()
        try:
            # Get the next feedback_id
            self.cursor.execute("SELECT MAX(feedback_id) FROM customer_feedback")
            max_id = self.cursor.fetchone()[0]
            next_id = 1 if max_id is None else max_id + 1

            self.cursor.execute("""
                INSERT INTO customer_feedback 
                (feedback_id, customer_id, service, rating, comment, date)
                VALUES (?, ?, ?, ?, ?, DATE('now'))
            """, (next_id, customer_id, service, rating, comment))
            
            self.conn.commit()
            return next_id
        except Exception as e:
            print(f"Error adding customer feedback: {str(e)}")
            return None
        finally:
            self.disconnect()

