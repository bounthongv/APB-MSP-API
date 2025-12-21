from flask import request, jsonify
import mysql.connector
import os
import hashlib

# --- Authentication ---
stored_token = os.getenv("API_TOKEN")

def token_required(f):
    """Decorator to protect routes with Bearer Token Authentication."""
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"msg": "Missing or invalid Authorization header"}), 401
        
        token = auth_header.split(" ")[1]
        
        if token != stored_token:
            return jsonify({"msg": "Invalid token"}), 401
        
        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper


# --- Database Configuration (MySQL on Ubuntu) ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "msp_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "msp_password")
DB_NAME = os.getenv("DB_NAME", "apb_msp")

def get_db_connection():
    """Establish a connection to the MySQL database."""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# --- Signature and Other Helpers ---
def string_sort(value):
    """Sort the characters in a string."""
    return ''.join(sorted(value))

def generate_signature(key_code, sign_date, order_no):
    """Generate a signature using keyCode, signDate, and trn_id."""
    concatenated = f"{key_code}{sign_date}{order_no}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

def generate_signature_apis(key_code, sign_date):
    """Generate a signature using keyCode, signDate"""
    concatenated = f"{key_code}{sign_date}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

def clean_string(value):
    """
    Strips leading/trailing whitespace from a string.
    Returns the original value if it's not a string.
    """
    if isinstance(value, str):
        return value.strip()
    return value