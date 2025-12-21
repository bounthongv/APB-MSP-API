from flask import Flask, request, Response, jsonify
import pyodbc
import json
import os
import hashlib
from datetime import datetime
# remove these function to shared_utils
from shared_utils import get_db_connection, token_required, generate_signature, \
string_sort, generate_signature_apis, clean_string

# Flask app
app = Flask(__name__)

# Define the decorator at the top
#stored_token = os.getenv("BEARER_TOKEN")
# I have saved earleir with different name
# stored_token = os.getenv("API_TOKEN")

# def token_required(f):
#     """Decorator to protect routes with Bearer Token Authentication."""
#     def wrapper(*args, **kwargs):
#         # Get the Authorization header
#         auth_header = request.headers.get("Authorization")
        
#         # Check if the Authorization header is provided and in the correct format
#         if not auth_header or not auth_header.startswith("Bearer "):
#             return jsonify({"msg": "Missing or invalid Authorization header"}), 401
        
#         # Extract the token
#         token = auth_header.split(" ")[1]
        
#         # Compare the provided token with the stored token
#         if token != stored_token:
#             return jsonify({"msg": "Invalid token"}), 401
        
#         return f(*args, **kwargs)

#     wrapper.__name__ = f.__name__  # Preserve the name of the original function
#     return wrapper




# # Retrieve database configuration from environment variables
# DB_HOST = os.getenv("DB_HOST", "localhost\\MSSQLSERVER")
# DB_PORT = os.getenv("DB_PORT", "1558")
# DB_USER = os.getenv("DB_USER", "APIS_TEST")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "apis@2025")
# DB_NAME = os.getenv("DB_NAME", "TaxAPI")


# # Secret key for HMAC signing (this should be stored securely)
# # SECRET_KEY = os.getenv('SECRET_KEY')


# def string_sort(value):
#     """Sort the characters in a string."""
#     return ''.join(sorted(value))

# def generate_signature(key_code, sign_date, order_no):
#     """Generate a signature using keyCode, signDate, and ORDER_NO."""
#     concatenated = f"{key_code}{sign_date}{order_no}"
#     sorted_string = string_sort(concatenated)
#     signature = hashlib.md5(sorted_string.encode()).hexdigest()
#     return signature

# def generate_signature_apis(key_code, sign_date):
#     """Generate a signature using keyCode, signDate"""
#     concatenated = f"{key_code}{sign_date}"
#     sorted_string = string_sort(concatenated)
#     signature = hashlib.md5(sorted_string.encode()).hexdigest()
#     return signature

# def get_db_connection():
#     """Establish a connection to the MSSQL database."""
#     connection_string = (
#         f"DRIVER={{ODBC Driver 17 for SQL Server}};"
#         f"SERVER={DB_HOST},{DB_PORT};"
#         f"DATABASE={DB_NAME};"
#         f"UID={DB_USER};"
#         f"PWD={DB_PASSWORD}"
#     )
#     return pyodbc.connect(connection_string)

@app.route('/', methods=['GET'])
def root():
    """Root endpoint to indicate the API is running."""
    return jsonify({"status": "API is running"}), 200

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "alive"}), 200


# Updated number-to-Lao conversion function
def number_to_words(number):
    units = ["", "ໜຶ່ງ", "ສອງ", "ສາມ", "ສີ່", "ຫ້າ", "ຫົກ", "ເຈັດ", "ແປດ", "ເກົ້າ"]
    teens = ["ສິບ", "ສິບເອັດ", "ສິບສອງ", "ສິບສາມ", "ສິບສີ່", "ສິບຫ້າ", "ສິບຫົກ",
             "ສິບເຈັດ", "ສິບແປດ", "ສິບເກົ້າ"]
    tens = ["", "ສິບ", "ຊາວ", "ສາມສິບ", "ສີ່ສິບ", "ຫ້າສິບ", "ຫົກສິບ", "ເຈັດສິບ",
            "ແປດສິບ", "ເກົ້າສິບ"]

    if number == 0:
        return "ສູນ"
    elif number < 10:
        return units[number]
    elif 10 <= number < 20:
        return teens[number - 10]
    elif 20 <= number < 100:
        if number % 10 == 1:
            return tens[number // 10] + "ເອັດ"
        else:
            return tens[number // 10] + ("" + number_to_words(number % 10) if number % 10 != 0 else "")
    elif 100 <= number < 1000:
        hundreds_digit = number // 100
        remainder = number % 100
        if remainder == 0:
            return units[hundreds_digit] + "ຮ້ອຍ"
        else:
            return units[hundreds_digit] + "ຮ້ອຍ" + number_to_words(remainder)
    elif 1000 <= number < 100000:
        thousands_part = number // 1000
        remainder = number % 1000
        thousands_word = number_to_words(thousands_part) + "ພັນ"
        if remainder == 0:
            return thousands_word
        else:
            return thousands_word + number_to_words(remainder)
    elif 100000 <= number < 1000000:  # Fix for 100,000 to 999,999
        hundred_thousands_part = number // 100000
        remainder = number % 100000
        hundred_thousands_word = number_to_words(hundred_thousands_part) + "ແສນ"
        if remainder == 0:
            return hundred_thousands_word
        else:
            return hundred_thousands_word + number_to_words(remainder)
    elif 1000000 <= number < 1000000000:
        millions_part = number // 1000000
        remainder = number % 1000000
        millions_word = number_to_words(millions_part) + "ລ້ານ"
        if remainder == 0:
            return millions_word
        else:
            return millions_word + number_to_words(remainder)
    elif 1000000000 <= number < 1000000000000:
        billions_part = number // 1000000000
        remainder = number % 1000000000
        billions_word = number_to_words(billions_part) + "ຕື້"
        if remainder == 0:
            return billions_word
        else:
            return billions_word + number_to_words(remainder)
    else:
        return "Number out of range"

def number_with_decimals_to_words(number):    
    """ Convert a number with up to two decimal places to words in Lao. """
    integer_part = int(number)
    decimal_part = round((number - integer_part) * 100)  # Extract two decimal places

    words = number_to_words(integer_part)  # Convert integer part correctly

    if decimal_part > 0:
        decimal_digits = str(decimal_part).zfill(2)  # Ensure two digits
        decimal_words = "ຈຸດ" + "".join([number_to_words(int(digit)) for digit in decimal_digits])
        return words + decimal_words
    else:
        return words

def float_to_words(number_str):
    if '.' in number_str:
        integer_part, decimal_part = number_str.split('.')
        integer_words = number_to_words(int(integer_part))

        decimal_part = decimal_part[:2].ljust(2, '0')  # Ensure two digits
        decimal_words = "ຈຸດ" + "".join([number_to_words(int(digit)) for digit in decimal_part])

        return integer_words + decimal_words
    else:
        return number_to_words(int(number_str))

@app.route('/number-to-words', methods=['POST'])
@token_required  # Add this line to protect the route
# @app.route('/number-to-words', methods=['POST'])
def convert_number_to_words():
    data = request.get_json()
    number_str = data.get('number')

    if number_str is None:
        return jsonify({"code": "400", "message": "Please provide a number"}), 400

    try:
        number_str = str(number_str)  # Keep it as a string to preserve format
        number = float(number_str)  # Convert to float for validation
    except ValueError:
        return jsonify({"code": "400", "message": "Invalid number provided"}), 400

    if number < 0 or number >= 1000000000000:  # Check range
        return jsonify({
            "code": "400",
            "message": "Number out of range. Please provide a number between 0 and 999,999,999,999"
        }), 400

    words = float_to_words(number_str)  # Convert number to words

    return jsonify({
        "code": "200",
        "data": {
            "number": number_str,  # Keep exactly as input
            "words": words
        },
        "message": "success"
    })

# --- THIS IS THE CRUCIAL PART ---
# Import and register your new expense blueprint
from msp_api import msp_bp
app.register_blueprint(msp_bp)

from expenses_api import expenses_bp
app.register_blueprint(expenses_bp)
# ----------------------------------

if __name__ == "__main__":
    # app.run(debug=False)
    app.run(host='0.0.0.0', port=5000, debug=True)