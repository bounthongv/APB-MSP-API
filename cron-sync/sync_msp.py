import os
import pyodbc
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from datetime import datetime
import decimal

# Load environment variables
load_dotenv()

# --- Configuration ---
# Local MySQL (Source)
MYSQL_CONFIG = {
    'host': os.getenv("DB_HOST", "localhost"),
    'user': os.getenv("DB_USER", "msp_user"),
    'password': os.getenv("DB_PASSWORD", "msp_password"),
    'database': os.getenv("DB_NAME", "apb_msp")
}

# Remote MSSQL (Destination)
MSSQL_CONFIG = {
    'server': '10.151.146.90',
    'database': 'FN_APB2025',
    'user': 'sa',
    'password': 'Apb@2k25',
    'driver': '{ODBC Driver 18 for SQL Server}'
}

# Fixed Constants from VB Code
OFFICE_ID = "00-00" # Equivalent to MuSubOff in VB (Assumed default, adjust if needed)
USER_ID = "API_BOT" # Equivalent to MUserID

def get_mssql_conn():
    conn_str = (
        f"DRIVER={MSSQL_CONFIG['driver']};"
        f"SERVER={MSSQL_CONFIG['server']};"
        f"DATABASE={MSSQL_CONFIG['database']};"
        f"UID={MSSQL_CONFIG['user']};"
        f"PWD={MSSQL_CONFIG['password']};"
        f"Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)

def get_mysql_conn():
    return mysql.connector.connect(**MYSQL_CONFIG)

def generate_certify_id(cursor, acc_book, bis_date, office_id_prefix):
    """
    Replicates the AutoNumber() logic from VB.NET.
    Format: <book><YYMM><7-digit-running-number>
    """
    year_str = bis_date.strftime("%Y")
    month_str = bis_date.strftime("%m")
    yymm = bis_date.strftime("%y%m")
    
    # Logic from VB:
    # SELECT top 1 Right(certify,7) As certify FROM gen_jn WHERE book = N'...' 
    # And year(date_work) = '...' And month(date_work) = '...' 
    # And LEFT(company,2)=N'...' Order by Right(certify,7) DESC
    
    query = """
        SELECT TOP 1 RIGHT(certify, 7) 
        FROM gen_jn 
        WHERE book = ? 
          AND YEAR(date_work) = ? 
          AND MONTH(date_work) = ? 
          AND LEFT(company, 2) = ? 
        ORDER BY RIGHT(certify, 7) DESC
    """
    
    cursor.execute(query, (acc_book, year_str, month_str, office_id_prefix))
    row = cursor.fetchone()
    
    if row and row[0] and row[0].strip().isdigit():
        next_num = int(row[0]) + 1
    else:
        next_num = 1
        
    running_num = f"{next_num:07d}"
    
    return f"{acc_book}{yymm}{running_num}"

def sync_data():
    mysql_conn = None
    mssql_conn = None
    
    try:
        print(f"[{datetime.now()}] Starting Sync Process...")
        
        # 1. Connect to DBs
        mysql_conn = get_mysql_conn()
        mysql_cursor = mysql_conn.cursor(dictionary=True)
        
        mssql_conn = get_mssql_conn()
        mssql_cursor = mssql_conn.cursor()

        # 2. Fetch Pending Records (Wait)
        mysql_cursor.execute("SELECT * FROM msp WHERE status = 'wait' ORDER BY trn_id")
        pending_records = mysql_cursor.fetchall()
        
        if not pending_records:
            print("No pending 'wait' records found.")
        else:
            print(f"Found {len(pending_records)} pending records.")
            
            for rec in pending_records:
                trn_id = rec['trn_id']
                print(f"Processing {trn_id}...")
                
                try:
                    # Check if already processed in MSSQL (Idempotency)
                    # Checking gen_jn directly via Referno (API field from VB code logic)
                    mssql_cursor.execute("SELECT COUNT(*) FROM gen_jn WHERE Referno = ? AND API = 'API'", (trn_id,))
                    if mssql_cursor.fetchone()[0] > 0:
                        print(f"  - Skipped: {trn_id} already exists in gen_jn.")
                        # Mark success in MySQL to stop retrying
                        mysql_cursor.execute("UPDATE msp SET status = 'success', update_date = NOW() WHERE trn_id = %s", (trn_id,))
                        mysql_conn.commit()
                        continue

                    # --- Step A: Prepare Data ---
                    # Fetch Details
                    mysql_cursor.execute("SELECT * FROM tbl_dr WHERE trn_id = %s", (trn_id,))
                    debits = mysql_cursor.fetchall()
                    
                    mysql_cursor.execute("SELECT * FROM tbl_cr WHERE trn_id = %s", (trn_id,))
                    credits = mysql_cursor.fetchall()

                    # Calculate Totals
                    sum_amt = sum(d['dr_amt'] for d in debits) if debits else 0
                    
                    # Prepare Header Variables
                    bis_date = rec['bis_date']
                    acc_book = rec['acc_book']
                    office_prefix = OFFICE_ID[:2] # First 2 chars for Company check
                    ex_rate = float(rec['ex_rate']) if rec['ex_rate'] else 1.0
                    if ex_rate == 0: ex_rate = 1.0
                    
                    # --- Step B: Generate Certify ID (AutoNumber) ---
                    # IMPORTANT: This must be done inside the loop for each transaction
                    certify_id = generate_certify_id(mssql_cursor, acc_book, bis_date, office_prefix)
                    
                    # --- Step C: Insert into gen_jn (Accounting Entries) ---
                    # Start Transaction
                    mssql_conn.autocommit = False
                    
                    # 1. Insert Debits
                    for dr in debits:
                        dr_amt = float(dr['dr_amt'])
                        dr_amt_lak = float(dr['dr_amt_lak']) if dr['dr_amt_lak'] else 0
                        dr_desc = dr['dr_desc'] if dr['dr_desc'] else rec['trn_desc']
                        
                        sql_dr = """
                            INSERT INTO gen_jn(
                                date_work, ac_Name, book, certify, Referno, descrip, descripe,
                                amount, curr, rate, Rate_USD, net_amt, code_dr, code_cr, ac_code,
                                amt_dr, amt_cr, amt_USD_Dr, amt_USD_Cr, amount_dr, amount_cr,
                                certis, lock, rec_lock, last_update, last_user, company, Office_ID, del, AG, Frm, API
                            ) VALUES (
                                ?, ?, ?, ?, ?, ?, '',
                                ?, ?, ?, ?, 0, ?, '', ?,
                                ?, 0, ?, 0, ?, 0,
                                3, 4, 5, ?, ?, ?, ?, 0, 1, 0, 'API'
                            )
                        """
                        # Calculations from VB:
                        # amount_dr = dr_amt / ex_rate
                        amount_dr_calc = dr_amt / ex_rate

                        mssql_cursor.execute(sql_dr, (
                            bis_date, rec['trn_desc'], acc_book, certify_id, trn_id, dr_desc,
                            float(sum_amt), rec['currency'], ex_rate, ex_rate, dr['dr_ac'], dr['dr_ac'],
                            dr_amt_lak, dr_amt, amount_dr_calc,
                            datetime.now(), USER_ID, OFFICE_ID, OFFICE_ID
                        ))

                    # 2. Insert Credits
                    for cr in credits:
                        cr_amt = float(cr['cr_amt'])
                        cr_amt_lak = float(cr['cr_amt_lak']) if cr['cr_amt_lak'] else 0
                        cr_desc = cr['cr_desc'] if cr['cr_desc'] else rec['trn_desc']
                        
                        sql_cr = """
                            INSERT INTO gen_jn(
                                date_work, ac_Name, book, certify, Referno, descrip, descripe,
                                amount, curr, rate, Rate_USD, net_amt, code_dr, code_cr, ac_code,
                                amt_dr, amt_cr, amt_USD_Dr, amt_USD_Cr, amount_dr, amount_cr,
                                certis, lock, rec_lock, last_update, last_user, company, Office_ID, del, AG, Frm, API
                            ) VALUES (
                                ?, ?, ?, ?, ?, ?, '',
                                ?, ?, ?, ?, 0, '', ?, ?,
                                '', ?, '', ?, 0, ?,
                                3, 4, 5, ?, ?, ?, ?, 0, 1, 0, 'API'
                            )
                        """
                        # Calculations from VB:
                        # amount_cr = cr_amt / ex_rate
                        amount_cr_calc = cr_amt / ex_rate

                        mssql_cursor.execute(sql_cr, (
                            bis_date, rec['trn_desc'], acc_book, certify_id, trn_id, cr_desc,
                            float(sum_amt), rec['currency'], ex_rate, ex_rate, cr['cr_ac'], cr['cr_ac'],
                            cr_amt_lak, cr_amt, amount_cr_calc,
                            datetime.now(), USER_ID, OFFICE_ID, OFFICE_ID
                        ))

                    # --- Step D: Commit & Update Status ---
                    mssql_conn.commit()
                    mssql_conn.autocommit = True # Reset
                    
                    print(f"  - Success: {trn_id} inserted with Certify ID {certify_id}")
                    
                    mysql_cursor.execute("UPDATE msp SET status = 'success', update_date = NOW() WHERE trn_id = %s", (trn_id,))
                    mysql_conn.commit()

                except Exception as e:
                    mssql_conn.rollback()
                    mssql_conn.autocommit = True
                    print(f"  - Error processing {trn_id}: {e}")
                    # Update fail reason
                    mysql_cursor.execute("UPDATE msp SET fail_reason = %s, update_date = NOW() WHERE trn_id = %s", (str(e)[:250], trn_id))
                    mysql_conn.commit()

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    finally:
        if mysql_conn: mysql_conn.close()
        if mssql_conn: mssql_conn.close()

if __name__ == "__main__":
    sync_data()
