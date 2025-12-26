from flask import Blueprint, request, jsonify
from shared_utils import get_db_connection, token_required

# Create a Blueprint object for APIS-related endpoints.
# All routes in this file will start with /apis
apis_bp = Blueprint('apis_api', __name__, url_prefix='/apis')

@apis_bp.route('/retrieve_msp_status', methods=['GET'])
@token_required
def retrieve_msp_by_status():
    """
    Retrieves records from the 'msp' table based on the 'status' parameter.
    """
    conn = None
    try:
        status = request.args.get("status")
        if not status:
            # Try getting from JSON body if not in args
            data = request.get_json(silent=True)
            if data and data.get("status"):
                status = data.get("status")
        
        if not status:
            return jsonify({"error": "Missing required parameter: status"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Selecting columns relevant to the record
        query = """
            SELECT trn_id, trn_desc, currency, acc_book, status, 
                   fail_reason, bis_date, create_date, update_date, ex_rate 
            FROM msp 
            WHERE status = %s
        """
        cursor.execute(query, (status,))
        records = cursor.fetchall()

        return jsonify({"code": "200", "data": records, "message": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@apis_bp.route('/retrieve_msp_trn_id', methods=['GET'])
@token_required
def retrieve_msp_by_trn_id():
    """
    Retrieves a record from the 'msp' table based on the 'trn_id' parameter.
    """
    conn = None
    try:
        trn_id = request.args.get("trn_id")
        if not trn_id:
            # Try getting from JSON body if not in args
            data = request.get_json(silent=True)
            if data and data.get("trn_id"):
                trn_id = data.get("trn_id")
        
        if not trn_id:
            return jsonify({"error": "Missing required parameter: trn_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Selecting columns relevant to the record
        query = """
            SELECT trn_id, trn_desc, currency, acc_book, status, 
                   fail_reason, bis_date, create_date, update_date, ex_rate 
            FROM msp 
            WHERE trn_id = %s
        """
        cursor.execute(query, (trn_id,))
        record = cursor.fetchone() # Assuming trn_id is unique, fetchone is appropriate

        if not record:
            return jsonify({"code": "404", "message": "Transaction not found"}), 404

        return jsonify({"code": "200", "data": record, "message": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@apis_bp.route('/retrieve_dr_trn_id', methods=['GET'])
@token_required
def retrieve_dr_by_trn_id():
    """
    Retrieves records from the 'tbl_dr' table based on the 'trn_id' parameter.
    """
    conn = None
    try:
        trn_id = request.args.get("trn_id")
        if not trn_id:
            data = request.get_json(silent=True)
            if data and data.get("trn_id"):
                trn_id = data.get("trn_id")
        
        if not trn_id:
            return jsonify({"error": "Missing required parameter: trn_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT trn_id, dr_ac, dr_amt, dr_amt_lak, dr_desc
            FROM tbl_dr 
            WHERE trn_id = %s
        """
        cursor.execute(query, (trn_id,))
        records = cursor.fetchall()

        if not records:
            return jsonify({"code": "404", "message": "Records not found"}), 404

        return jsonify({"code": "200", "data": records, "message": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

        return jsonify({"code": "200", "data": records, "message": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@apis_bp.route('/update_status', methods=['PATCH'])
@token_required
def update_msp_status():
    """
    Updates the status (and optionally fail_reason) of a record in the 'msp' table.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        trn_id = data.get("trn_id")
        status = data.get("status")
        fail_reason = data.get("fail_reason", None)

        if not trn_id or not status:
            return jsonify({"error": "Missing required fields: trn_id, status"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if record exists
        cursor.execute("SELECT status FROM msp WHERE trn_id = %s", (trn_id,))
        record = cursor.fetchone()
        if not record:
            return jsonify({"error": f"No record found with trn_id '{trn_id}'"}), 404

        # Perform update
        query = "UPDATE msp SET status = %s, fail_reason = %s WHERE trn_id = %s"
        cursor.execute(query, (status, fail_reason, trn_id))
        conn.commit()

        return jsonify({
            "code": "200",
            "data": {"trn_id": trn_id, "status": status},
            "message": "Status updated successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@apis_bp.route('/confirm_cancel', methods=['PATCH'])
@token_required
def confirm_msp_cancel():
    """
    Updates the status of a record from 'cancel' to 'canceled' after successful reverse accounting.
    """
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        trn_id = data.get("trn_id")
        
        if not trn_id:
            return jsonify({"error": "Missing required field: trn_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if record exists and has status 'cancel'
        cursor.execute("SELECT status FROM msp WHERE trn_id = %s", (trn_id,))
        record = cursor.fetchone()
        
        if not record:
            return jsonify({"error": f"No record found with trn_id '{trn_id}'"}), 404
        
        current_status = record[0] if isinstance(record, tuple) else record['status'] # Handle different cursor types
        
        if current_status != 'cancel':
            return jsonify({
                "error": f"Cannot confirm cancel. Current status is '{current_status}', expected 'cancel'."
            }), 400

        # Perform update to 'canceled'
        query = "UPDATE msp SET status = 'canceled' WHERE trn_id = %s"
        cursor.execute(query, (trn_id,))
        conn.commit()

        return jsonify({
            "code": "200",
            "data": {"trn_id": trn_id, "status": "canceled"},
            "message": "Cancellation confirmed successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
