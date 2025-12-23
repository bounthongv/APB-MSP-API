from dotenv import load_dotenv
import os

# 1. Load environment variables FIRST before any other imports
load_dotenv()

# 2. Now import the connection helper
from shared_utils import get_db_connection

def test_connection():
    try:
        # Debug: Print which user we are trying to connect with
        print(f"Attempting to connect to host: {os.getenv('DB_HOST')}")
        print(f"Using database user: {os.getenv('DB_USER')}")
        
        print("Connecting to database...")
        conn = get_db_connection()
        
        if conn.is_connected():
            print("Successfully connected to the database!")
            
            db_info = conn.get_server_info()
            print(f"Connected to MySQL Server version: {db_info}")
            
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            print(f"You're connected to database: {record[0]}")
            
            cursor.close()
            conn.close()
            print("Connection closed.")
        else:
            print("Failed to connect.")
    except Exception as e:
        print(f"Error while connecting to MySQL: {e}")

if __name__ == "__main__":
    test_connection()