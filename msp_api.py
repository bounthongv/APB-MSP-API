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
    Receives an MSP JSON payload and inserts it into the 
    'msp', 'tbl_dr', and 'tbl_cr' tables using trn_id as the link.
    """
    conn = None
    try:
        # --- 1. Parse and Validate the Request Payload ---
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid or empty JSON input"}), 400

        # Mandatory root fields
        trn_id = clean_string(data.get("trn_id"))
        trn_desc = data.get("trn_desc")
        currency = data.get("currency")
        acc_book = data.get("acc_book")
        bis_date = data.get("bis_date")
        status = data.get("status")
        create_date = data.get("create_date")
        
        # ex_rate logic based on currency
        ex_rate = data.get("ex_rate")
        is_local_currency = (currency == 'LAK')

        if is_local_currency:
            if ex_rate is None:
                ex_rate = Decimal('1.00')
            else:
                ex_rate = Decimal(str(ex_rate))
        else:
            # Foreign currency
            if ex_rate is None:
                return jsonify({"error": "Missing required field: ex_rate (required for foreign currency)"}), 400
            ex_rate = Decimal(str(ex_rate))
            if ex_rate == Decimal('1.00') or ex_rate == Decimal('1'):
                 return jsonify({"error": "ex_rate must not be 1 for foreign currency"}), 400
        
        # Mandatory lists
        debit_entries = data.get("debit")
        credit_entries = data.get("credit")

        # Validate presence of required root fields
        if not all([trn_id, trn_desc, currency, acc_book, bis_date, status, create_date, debit_entries, credit_entries]):
            return jsonify({"error": "Missing required fields: trn_id, trn_desc, currency, acc_book, bis_date, status, create_date, debit, or credit"}), 400

        # --- 2. Validate Entries and Calculate Totals ---
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        
        final_debit_entries = []
        final_credit_entries = []

        try:
            # Calculate total debit and validate LAK amounts
            for item in debit_entries:
                if not all(k in item for k in ['dr_ac', 'dr_amt']):
                    return jsonify({"error": "A debit entry is missing 'dr_ac' or 'dr_amt'"}), 400
                
                amount_str = str(item.get('dr_amt', '0')).replace(',', '')
                dr_amt = Decimal(amount_str)
                total_debit += dr_amt
                
                # Logic for dr_amt_lak
                dr_amt_lak_val = item.get('dr_amt_lak')
                if is_local_currency:
                    # Optional, defaults to dr_amt
                    if dr_amt_lak_val is None:
                        dr_amt_lak = dr_amt
                    else:
                        dr_amt_lak = Decimal(str(dr_amt_lak_val).replace(',', ''))
                else:
                    # Mandatory and must != dr_amt
                    if dr_amt_lak_val is None:
                         return jsonify({"error": "Missing 'dr_amt_lak' for foreign currency debit entry"}), 400
                    dr_amt_lak = Decimal(str(dr_amt_lak_val).replace(',', ''))
                    if dr_amt_lak == dr_amt:
                        return jsonify({"error": "dr_amt_lak must be different from dr_amt for foreign currency"}), 400
                
                # Store processed item to avoid re-parsing
                final_item = item.copy()
                final_item['dr_amt_decimal'] = dr_amt
                final_item['dr_amt_lak_decimal'] = dr_amt_lak
                final_debit_entries.append(final_item)

            # Calculate total credit and validate LAK amounts
            for item in credit_entries:
                if not all(k in item for k in ['cr_ac', 'cr_amt']):
                    return jsonify({"error": "A credit entry is missing 'cr_ac' or 'cr_amt'"}), 400
                
                amount_str = str(item.get('cr_amt', '0')).replace(',', '')
                cr_amt = Decimal(amount_str)
                total_credit += cr_amt
                
                # Logic for cr_amt_lak
                cr_amt_lak_val = item.get('cr_amt_lak')
                if is_local_currency:
                    # Optional, defaults to cr_amt
                    if cr_amt_lak_val is None:
                        cr_amt_lak = cr_amt
                    else:
                        cr_amt_lak = Decimal(str(cr_amt_lak_val).replace(',', ''))
                else:
                     # Mandatory and must != cr_amt
                    if cr_amt_lak_val is None:
                         return jsonify({"error": "Missing 'cr_amt_lak' for foreign currency credit entry"}), 400
                    cr_amt_lak = Decimal(str(cr_amt_lak_val).replace(',', ''))
                    if cr_amt_lak == cr_amt:
                        return jsonify({"error": "cr_amt_lak must be different from cr_amt for foreign currency"}), 400

                # Store processed item
                final_item = item.copy()
                final_item['cr_amt_decimal'] = cr_amt
                final_item['cr_amt_lak_decimal'] = cr_amt_lak
                final_credit_entries.append(final_item)

        except (InvalidOperation, TypeError, KeyError) as e:
            return jsonify({"error": f"Invalid amount format in entries. Details: {e}"}), 400

        if total_debit != total_credit:
            return jsonify({
                "error": "Debit and Credit totals do not match.",
                "data": {"total_debit": str(total_debit), "total_credit": str(total_credit)}
            }), 400

        # --- 3. Database Operations ---
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert into main 'msp' table
        msp_query = """
            INSERT INTO msp (trn_id, trn_desc, currency, acc_book, status, bis_date, create_date, ex_rate)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(msp_query, (trn_id, trn_desc, currency, acc_book, status, bis_date, create_date, ex_rate))

        # Insert into 'tbl_dr' using trn_id
        dr_query = "INSERT INTO tbl_dr (trn_id, dr_ac, dr_amt, dr_amt_lak, dr_desc) VALUES (%s, %s, %s, %s, %s)"
        for item in final_debit_entries:
            dr_ac = clean_string(item.get('dr_ac'))
            dr_amt = item['dr_amt_decimal']
            dr_amt_lak = item['dr_amt_lak_decimal']
            dr_desc = item.get('dr_desc') 
            cursor.execute(dr_query, (trn_id, dr_ac, dr_amt, dr_amt_lak, dr_desc))
        
        # Insert into 'tbl_cr' using trn_id
        cr_query = "INSERT INTO tbl_cr (trn_id, cr_ac, cr_amt, cr_amt_lak, cr_desc) VALUES (%s, %s, %s, %s, %s)"
        for item in final_credit_entries:
            cr_ac = clean_string(item.get('cr_ac'))
            cr_amt = item['cr_amt_decimal']
            cr_amt_lak = item['cr_amt_lak_decimal']
            cr_desc = item.get('cr_desc') 
            cursor.execute(cr_query, (trn_id, cr_ac, cr_amt, cr_amt_lak, cr_desc))

        conn.commit()

        return jsonify({
            "code": "200",
            "data": {"trn_id": trn_id},
            "message": "MSP transaction uploaded successfully"
        }), 201

    except mysql.connector.Error as e:
        if e.errno == 1062:
             return jsonify({"error": f"Duplicate entry: trn_id '{trn_id}' already exists."}), 409
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@msp_bp.route('/getStatus', methods=['POST'])
@token_required
def get_msp_status():
    """Checks processing status by trn_id."""
    conn = None
    try:
        data = request.get_json()
        trn_id = data.get("trn_id") if data else None
        if not trn_id:
            return jsonify({"error": "Missing required field: trn_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT trn_id, status, fail_reason, create_date, update_date FROM msp WHERE trn_id = %s"
        cursor.execute(query, (trn_id,))
        msp_record = cursor.fetchone()

        if not msp_record:
            return jsonify({"error": f"No MSP transaction found with trn_id '{trn_id}'."}), 404

        return jsonify({"code": "200", "data": msp_record, "message": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@msp_bp.route('/cancel', methods=['POST'])
@token_required
def cancel_msp():
    """Updates status to 'cancel' for a given trn_id."""
    conn = None
    try:
        data = request.get_json()
        trn_id = data.get("trn_id") if data else None
        if not trn_id:
            return jsonify({"error": "Missing required field: trn_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM msp WHERE trn_id = %s", (trn_id,))
        msp_record = cursor.fetchone()

        if not msp_record:
            return jsonify({"error": "Not found"}), 404
        if msp_record['status'] == 'cancel':
            return jsonify({"error": "Already canceled"}), 400
        if msp_record['status'] not in ['wait', 'success']:
            return jsonify({"error": "Cannot cancel in current status"}), 400

        cursor.execute("UPDATE msp SET status = 'cancel' WHERE trn_id = %s", (trn_id,))
        conn.commit()
        return jsonify({"code": "200", "data": {"trn_id": trn_id, "status": "cancel"}, "message": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@msp_bp.route('/searchByDate', methods=['POST'])
@token_required
def search_msp_by_date():
    """Searches for records by bis_date range."""
    conn = None
    try:
        data = request.get_json()
        search_data = data.get("Data") if data else None
        if not search_data: return jsonify({"error": "Missing 'Data' object"}), 400

        start = search_data.get("startDate")
        end = search_data.get("endDate")
        if not start or not end: return jsonify({"error": "Missing date range"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT trn_id, status, fail_reason, bis_date, create_date, update_date FROM msp WHERE DATE(bis_date) BETWEEN %s AND %s"
        cursor.execute(query, (start, end))
        records = cursor.fetchall()
        return jsonify({"code": "200", "data": records, "message": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@msp_bp.route('/retrieve', methods=['GET'])
@token_required
def retrieve_msp():
    """Retrieves records by status."""
    conn = None
    try:
        status = request.args.get("status")
        if not status:
            data = request.get_json(silent=True)
            if data and data.get("Data"): status = data.get("Data").get("status")
        
        if not status: return jsonify({"error": "Missing status"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT trn_id, status, fail_reason, create_date, update_date FROM msp WHERE status = %s", (status,))
        records = cursor.fetchall()
        return jsonify({"code": "200", "data": records, "message": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()