import os
import sys
import pyodbc
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from datetime import datetime, timedelta
import decimal
import logging

# ─── LOGGING SETUP ─────────────────────────────────────────────
LOG_FILE = os.getenv("SYNC_LOG", "/var/log/apb_sync.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("apb_sync")

# Load environment variables
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    # However, for finding the .env file which is EXTERNAL to the exe,
    # we want the directory of the executable itself.
    script_dir = os.path.dirname(sys.executable)
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(script_dir, '.env')
load_dotenv(env_path)

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
    'server': os.getenv("MSSQL_HOST", '10.151.146.90'),
    'database': os.getenv("MSSQL_DB", 'FN_APB2025'),
    'user': os.getenv("MSSQL_USER", 'sa'),
    'password': os.getenv("MSSQL_PASSWORD", 'Apb@2k25'),
    'driver': os.getenv("MSSQL_DRIVER", '{ODBC Driver 18 for SQL Server}')
}

# Fixed Constants from VB Code
OFFICE_ID = os.getenv("OFFICE_ID", "01-02")  # Confirmed correct with APB
USER_ID = os.getenv("USER_ID", "API_BOT")     # Equivalent to MUserID

# Retry settings
RETRY_WINDOW_SECONDS = int(os.getenv("SYNC_RETRY_WINDOW", "86400"))  # 24 hours

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
        logger.info("Starting Sync Process...")

        mysql_conn = get_mysql_conn()
        mysql_cursor = mysql_conn.cursor(dictionary=True)

        mssql_conn = get_mssql_conn()
        mssql_cursor = mssql_conn.cursor()

        # Fetch ALL non-success records (wait + cancel + fail), ordered by oldest first
        # This allows retry for failed records within the 24-hour window
        mysql_cursor.execute("""
            SELECT * FROM msp
            WHERE status IN ('wait', 'cancel', 'fail')
            ORDER BY update_date ASC, trn_id
        """)
        pending_records = mysql_cursor.fetchall()

        if not pending_records:
            logger.info("No pending records (wait/cancel/fail) found.")
        else:
            logger.info(f"Found {len(pending_records)} pending records.")

            for rec in pending_records:
                trn_id = rec['trn_id']
                status = rec.get('status', 'wait')
                fail_reason = rec.get('fail_reason', '') or ''
                update_date = rec.get('update_date')

                # Handle 'fail' records: retry within window, clear if expired
                if status == 'fail':
                    if update_date:
                        try:
                            fail_age = (datetime.now() - update_date).total_seconds()
                        except TypeError:
                            fail_age = 0
                    else:
                        fail_age = RETRY_WINDOW_SECONDS + 1

                    if fail_age >= RETRY_WINDOW_SECONDS:
                        logger.warning(
                            f"===== ALERT: {trn_id} still failing after {fail_age:.0f}s "
                            f"(>{RETRY_WINDOW_SECONDS/3600:.0f}h). "
                            f"Reason: {fail_reason[:200]}. "
                            f"Resetting to 'wait' for continued retry. "
                            f"Check log: tail -f {LOG_FILE} ====="
                        )
                        # Reset to 'wait' so it keeps trying
                        mysql_cursor.execute(
                            "UPDATE msp SET status = 'wait', fail_reason = NULL, update_date = NOW() WHERE trn_id = %s",
                            (trn_id,)
                        )
                        mysql_conn.commit()
                        # Re-read the record for processing
                        mysql_cursor.execute("SELECT * FROM msp WHERE trn_id = %s", (trn_id,))
                        rec = mysql_cursor.fetchone()
                        status = 'wait'
                        fail_reason = ''
                    else:
                        logger.info(f"  - {trn_id}: retrying (failed {fail_age:.0f}s ago)")
                elif status == 'cancel':
                    pass  # Handled by sync_cancellations

                logger.info(f"Processing {trn_id} (status={status})...")

                try:
                    # ─── IDEMPOTENCY CHECK (DUPLICATE PREVENTION) ───
                    # Key on the transaction's natural key ONLY (Referno + API).
                    # Do NOT filter by company prefix here: if a record was
                    # inserted under a different office in the past, filtering
                    # by LEFT(company,2) would MISS it and cause a DUPLICATE
                    # re-insert. Any existing row with this Referno means the
                    # transaction is already posted — skip it.
                    mssql_cursor.execute(
                        "SELECT COUNT(*) FROM gen_jn WHERE Referno = ? AND API = 'API'",
                        (trn_id,)
                    )
                    count = mssql_cursor.fetchone()[0]

                    if count > 0:
                        logger.info(f"  - Verified exists in gen_jn. Marking success (no re-insert, no duplicate).")
                        mysql_cursor.execute(
                            "UPDATE msp SET status = 'success', fail_reason = NULL, update_date = NOW() WHERE trn_id = %s",
                            (trn_id,)
                        )
                        mysql_conn.commit()
                        continue

                    # --- Step A: Prepare Data ---
                    mysql_cursor.execute("SELECT * FROM tbl_dr WHERE trn_id = %s", (trn_id,))
                    debits = mysql_cursor.fetchall()

                    mysql_cursor.execute("SELECT * FROM tbl_cr WHERE trn_id = %s", (trn_id,))
                    credits = mysql_cursor.fetchall()

                    # Calculate Totals
                    sum_amt = sum(d['dr_amt'] for d in debits) if debits else 0

                    # Prepare Header Variables
                    bis_date = rec['bis_date']
                    acc_book = rec['acc_book']
                    office_prefix = OFFICE_ID[:2]  # First 2 chars for Company check
                    ex_rate = float(rec['ex_rate']) if rec['ex_rate'] else 1.0
                    if ex_rate == 0: ex_rate = 1.0

                    # --- Step B: Generate Certify ID (AutoNumber) ---
                    certify_id = generate_certify_id(mssql_cursor, acc_book, bis_date, office_prefix)

                    # --- Step C: Insert into gen_jn (Accounting Entries) ---
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
                        amount_cr_calc = cr_amt / ex_rate

                        mssql_cursor.execute(sql_cr, (
                            bis_date, rec['trn_desc'], acc_book, certify_id, trn_id, cr_desc,
                            float(sum_amt), rec['currency'], ex_rate, ex_rate, cr['cr_ac'], cr['cr_ac'],
                            cr_amt_lak, cr_amt, amount_cr_calc,
                            datetime.now(), USER_ID, OFFICE_ID, OFFICE_ID
                        ))

                    # --- Step D: Commit & Update Status ---
                    # CRITICAL: Only mark success AFTER the MSSQL commit succeeds
                    mssql_conn.commit()
                    mssql_conn.autocommit = True

                    logger.info(f"  - Success: {trn_id} inserted with Certify ID {certify_id}")

                    mysql_cursor.execute(
                        "UPDATE msp SET status = 'success', fail_reason = NULL, update_date = NOW() WHERE trn_id = %s",
                        (trn_id,)
                    )
                    mysql_conn.commit()

                except Exception as e:
                    # ROLLBACK MSSQL and mark MySQL as 'fail' so it retries next cycle
                    if mssql_conn:
                        mssql_conn.rollback()
                        mssql_conn.autocommit = True

                    err_msg = str(e)[:250]
                    logger.error(f"  - Error processing {trn_id}: {e}")

                    mysql_cursor.execute(
                        "UPDATE msp SET status = 'fail', fail_reason = %s, update_date = NOW() WHERE trn_id = %s",
                        (err_msg, trn_id)
                    )
                    mysql_conn.commit()

    except Exception as e:
        logger.critical(f"CRITICAL ERROR: {e}")
        print(f"CRITICAL ERROR: {e}")
    finally:
        if mysql_conn: mysql_conn.close()
        if mssql_conn: mssql_conn.close()

def sync_cancellations():
    """
    Handles records with status='cancel'.
    Logic from VB: DELETE gen_jn WHERE API='API' AND Referno=trn_id
    """
    mysql_conn = None
    mssql_conn = None

    try:
        logger.info("Starting Cancellation Sync...")

        mysql_conn = get_mysql_conn()
        mysql_cursor = mysql_conn.cursor(dictionary=True)

        mssql_conn = get_mssql_conn()
        mssql_cursor = mssql_conn.cursor()

        # Fetch Pending Cancellations
        mysql_cursor.execute("SELECT * FROM msp WHERE status = 'cancel' ORDER BY trn_id")
        cancel_records = mysql_cursor.fetchall()

        if not cancel_records:
            logger.info("No pending 'cancel' records found.")
        else:
            logger.info(f"Found {len(cancel_records)} records to cancel.")

            for rec in cancel_records:
                trn_id = rec['trn_id']
                logger.info(f"Cancelling {trn_id}...")

                try:
                    # Start MSSQL Transaction
                    mssql_conn.autocommit = False

                    # Delete from gen_jn
                    mssql_cursor.execute("DELETE FROM gen_jn WHERE API='API' AND Referno = ?", (trn_id,))
                    row_count = mssql_cursor.rowcount

                    mssql_conn.commit()
                    mssql_conn.autocommit = True

                    if row_count > 0:
                        logger.info(f"  - Deleted {row_count} rows from gen_jn.")
                    else:
                        logger.info(f"  - No rows found in gen_jn to delete.")

                    # ONLY mark canceled after MSSQL delete succeeds
                    mysql_cursor.execute(
                        "UPDATE msp SET status = 'canceled', fail_reason = NULL, update_date = NOW() WHERE trn_id = %s",
                        (trn_id,)
                    )
                    mysql_conn.commit()
                    logger.info(f"  - Status updated to 'canceled' in MySQL.")

                except Exception as e:
                    if mssql_conn:
                        mssql_conn.rollback()
                        mssql_conn.autocommit = True

                    err_msg = f"Cancel Error: {str(e)[:200]}"
                    logger.error(f"  - Error cancelling {trn_id}: {e}")

                    mysql_cursor.execute(
                        "UPDATE msp SET status = 'fail', fail_reason = %s, update_date = NOW() WHERE trn_id = %s",
                        (err_msg, trn_id)
                    )
                    mysql_conn.commit()

    except Exception as e:
        logger.critical(f"CRITICAL ERROR IN CANCELLATION: {e}")
        print(f"CRITICAL ERROR IN CANCELLATION: {e}")
    finally:
        if mysql_conn: mysql_conn.close()
        if mssql_conn: mssql_conn.close()

if __name__ == "__main__":
    sync_data()
    sync_cancellations()