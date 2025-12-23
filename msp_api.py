from flask import Blueprint, request, Response, jsonify
import json
import mysql.connector
from decimal import Decimal, InvalidOperation
from shared_utils import get_db_connection, token_required, clean_string

# Create a Blueprint object for all MSP-related endpoints.
# All routes in this file will start with /msp
msp_bp = Blueprint('msp_api', __name__, url_prefix='/msp')

@msp_bp.route('/upload', methods=['POST'])
@token_required
def upload_msp():
    """
    Receives an MSP JSON payload, validates it, and inserts it into the 
    'msp', 'tbl_dr', and 'tbl_cr' tables.
    """
    conn = None
    try:
        # --- 1. Parse and Validate the Request Payload ---
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Extract fields from the root level
        # Removed security fields: keyCode, signDate, sign
        trn_id = clean_string(data.get("trn_id"))
        trn_desc = data.get("trn_desc")
        bis_date = data.get("bis_date")
        
        # Entries are provided at the root level
        debit_entries = data.get("debit")
        credit_entries = data.get("credit")

        # Validate presence of required fields
        if not all([trn_id, trn_desc, bis_date, debit_entries, credit_entries]):
            return jsonify({"error": "Missing required fields: trn_id, trn_desc, bis_date, debit, or credit"}), 400

        # --- 2. Validate Debit and Credit Entries ---
        if not isinstance(debit_entries, list) or len(debit_entries) == 0:
            return jsonify({"error": "Invalid or empty 'debit' array"}), 400
        if not isinstance(credit_entries, list) or len(credit_entries) == 0:
            return jsonify({"error": "Invalid or empty 'credit' array"}), 400

        # --- 3. Core Business Logic: Sum and Compare Debit/Credit Amounts ---
        total_debit = Decimal('0')
        total_credit = Decimal('0')

        try:
            for item in debit_entries:
                amount_str = str(item.get('dr_amt', '0')).replace(',', '')
                total_debit += Decimal(amount_str)

            for item in credit_entries:
                amount_str = str(item.get('cr_amt', '0')).replace(',', '')
                total_credit += Decimal(amount_str)

        except (InvalidOperation, TypeError, KeyError) as e:
            return jsonify({"error": f"Invalid amount format in debit/credit entries. Details: {e}"}), 400

        if total_debit != total_credit:
            return jsonify({
                "error": "Debit and Credit totals do not match.",
                "data": {
                    "total_debit": str(total_debit),
                    "total_credit": str(total_credit)
                }
            }), 400

        # --- 4. Database Operations ---
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into the main 'msp' table
        # Status defaults to 'wait'
        msp_query = """
            INSERT INTO msp (trn_id, trn_desc, status, bis_date)
            VALUES (%s, %s, 'wait', %s)
        """
        cursor.execute(msp_query, (trn_id, trn_desc, bis_date))
        
        # Retrieve the generated ID (MySQL style)
        msp_id = cursor.lastrowid
        
        if not msp_id:
             conn.rollback()
             return jsonify({"error": "Failed to insert into msp table: could not retrieve generated ID."}), 500

        # Insert into 'tbl_dr' using %s placeholders
        dr_query = "INSERT INTO tbl_dr (id, db_ac, db_amt) VALUES (%s, %s, %s)"
        for item in debit_entries:
            if not all(k in item for k in ['dr_ac', 'dr_amt']):
                conn.rollback()
                return jsonify({"error": "A debit entry is missing a required field (dr_ac, or dr_amt)"}), 400
            
            db_ac = clean_string(item.get('dr_ac'))
            db_amt = Decimal(str(item.get('dr_amt', '0')).replace(',', ''))
            cursor.execute(dr_query, (msp_id, db_ac, db_amt))
        
        # Insert into 'tbl_cr' using %s placeholders
        cr_query = "INSERT INTO tbl_cr (id, cr_ac, cr_amt) VALUES (%s, %s, %s)"
        for item in credit_entries:
            if not all(k in item for k in ['cr_ac', 'cr_amt']):
                conn.rollback()
                return jsonify({"error": "A credit entry is missing a required field (cr_ac, or cr_amt)"}), 400

            cr_ac = clean_string(item.get('cr_ac'))
            cr_amt = Decimal(str(item.get('cr_amt', '0')).replace(',', ''))
            cursor.execute(cr_query, (msp_id, cr_ac, cr_amt))

        conn.commit()

        # --- 5. Return Success Response ---
        return jsonify({
            "code": "200",
            "data": {
                "trn_id": trn_id
            },
            "message": "MSP transaction uploaded successfully"
        }), 201

    except mysql.connector.Error as e:
        if e.errno == 1062: # Duplicate entry
             return jsonify({"error": f"Duplicate entry: An MSP transaction with trn_id '{trn_id}' already exists."}), 409
        else:
            return jsonify({"error": f"Database error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@msp_bp.route('/getStatus', methods=['POST'])
@token_required
def get_msp_status():
    """
    Checks the processing status of a previously uploaded MSP transaction by its trn_id.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Removed security fields
        trn_id = data.get("trn_id")

        if not trn_id:
            return jsonify({"error": "Missing required field: trn_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT trn_id, status, fail_reason, create_date, update_date FROM msp WHERE trn_id = %s"
        cursor.execute(query, (trn_id,))
        msp_record = cursor.fetchone()

        if not msp_record:
            return jsonify({
                "error": f"No MSP transaction found with trn_id '{trn_id}'."
            }), 404

        return jsonify({
            "code": "200",
            "data": msp_record,
            "message": "MSP transaction status retrieved successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@msp_bp.route('/cancel', methods=['PATCH'])
@token_required
def cancel_msp():
    """
    Requests to cancel an existing MSP transaction by updating its status to 'cancel'.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Removed security fields
        trn_id = data.get("trn_id")

        if not trn_id:
            return jsonify({"error": "Missing required field: trn_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        check_query = "SELECT status FROM msp WHERE trn_id = %s"
        cursor.execute(check_query, (trn_id,))
        msp_record = cursor.fetchone()

        if not msp_record:
            return jsonify({"error": f"No MSP transaction found with trn_id '{trn_id}'."}), 404

        if msp_record['status'] == 'cancel':
            return jsonify({"error": f"MSP transaction with trn_id '{trn_id}' is already canceled."}), 400

        if msp_record['status'] not in ['wait', 'success']:
            return jsonify({"error": f"MSP transaction with trn_id '{trn_id}' cannot be cancelled. Only transactions with status 'wait' or 'success' can be cancelled."}), 400

        cancel_query = "UPDATE msp SET status = 'cancel' WHERE trn_id = %s"
        cursor.execute(cancel_query, (trn_id,))
        conn.commit()

        return jsonify({
            "code": "200",
            "data": {"trn_id": trn_id, "status": "cancel"},
            "message": f"Request to cancel MSP transaction '{trn_id}' was successful."
        }), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@msp_bp.route('/searchByDate', methods=['POST'])
@token_required
def search_msp_by_date():
    """
    Searches for MSP records created within a specified date range.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Removed security fields
        
        search_data = data.get("Data")
        if not search_data:
             return jsonify({"error": "Missing 'Data' object in the payload"}), 400

        start_date_str = search_data.get("startDate")
        end_date_str = search_data.get("endDate")

        if not all([start_date_str, end_date_str]):
            return jsonify({"error": "Missing required fields: startDate, or endDate"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT trn_id, status, fail_reason, create_date, update_date
            FROM msp
            WHERE DATE(create_date) BETWEEN %s AND %s
            ORDER BY create_date ASC
        """
        cursor.execute(query, (start_date_str, end_date_str))
        records = cursor.fetchall()

        return jsonify({
            "code": "200",
            "data": records,
            "message": "MSP records retrieved successfully."
        }), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()


@msp_bp.route('/retrieve', methods=['GET'])
@token_required
def retrieve_msp():
    """
    Retrieves all MSP records that match a given status.
    """
    conn = None
    try:
        data = request.get_json(silent=True)
        status_to_retrieve = None

        # Check query parameters first
        status_to_retrieve = request.args.get("status")

        # Fallback to JSON if not in query parameters
        if not status_to_retrieve and data:
            search_data = data.get("Data")
            if search_data:
                status_to_retrieve = search_data.get("status")

        allowed_statuses = ['wait', 'cancel', 'pending', 'success', 'fail']
        if not status_to_retrieve or status_to_retrieve not in allowed_statuses:
            return jsonify({
                "error": "Missing or invalid 'status'.",
                "allowed_values": allowed_statuses
            }), 400

        # Removed security checks (keyCode, signDate, sign, trn_id logic for this endpoint)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT `trn_id`, `status`, `fail_reason`, `create_date`, `update_date` FROM `msp` WHERE `status` = %s ORDER BY `create_date` ASC"
        cursor.execute(query, (status_to_retrieve,))
        records = cursor.fetchall()

        return jsonify({
            "code": "200",
            "data": records,
            "message": f"MSP records with status '{status_to_retrieve}' retrieved successfully."
        }), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()
