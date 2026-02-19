 Project Summary
  This is a Financial Transaction Gateway designed to bridge a web-based entry system with a legacy MSSQL accounting system. It consists of a Flask API
  for data capture and a specialized synchronization service.


  Transaction Capture & Sync Workflow
  Your Python service follows a two-stage "Capture and Push" model:


  1. Data Capture (Flask API - `msp_api.py`)
   * Source: Receives JSON payloads via the /msp/upload endpoint.
   * Validation: It enforces strict accounting rules, ensuring that the total Debit equals the total Credit before any data is saved.
   * Storage: The transaction is stored in a local MySQL database across three tables:
       * msp: Header information (trn_id, currency, bis_date, status).
       * tbl_dr: Detailed Debit entries (dr_ac, dr_amt, dr_amt_lak).
       * tbl_cr: Detailed Credit entries (cr_ac, cr_amt, cr_amt_lak).
   * Initial Status: Transactions are saved with a status of 'wait'.


  2. Synchronization (Cron Service - `sync_msp.py`)
  This script acts as the bridge to the APIS Account System:
   * Fetch: It retrieves all records from MySQL where status = 'wait'.
   * Account ID Generation: It replicates the accounting system's AutoNumber() logic to generate a unique certify ID (e.g.,
     <book><YYMM><running-number>).
   * MSSQL Injection: It translates the local MySQL rows into the MSSQL gen_jn (General Journal) table:
       * Debits are inserted with the account code in code_dr.
       * Credits are inserted with the account code in code_cr.
       * All entries are tagged with API = 'API' for identification.
   * Cancellations: If a record is marked as 'cancel' in MySQL, the service automatically deletes the corresponding journal entries from MSSQL gen_jn.
   * Status Update: Once the MSSQL transaction is committed, the script updates the MySQL record to 'success'.


  Confirmation
  Yes, your Python service specifically captures journal entries (debit/credit) from a MySQL database and inserts them into the MSSQL `gen_jn` table of
  the APIS account system. It also handles the complex mapping of exchange rates (ex_rate) and local currency conversions (amt_dr_lak/amt_cr_lak)
  required by the accounting system.

1. Who updates the status to "success"?
  Yes, the status is updated to "success" by your synchronization service (`sync_msp.py`).
   * When you first upload a transaction via the API, it is saved in your local MySQL database with the status `'wait'`.
   * The sync_msp.py script runs (via a Cron job), picks up those 'wait' records, and attempts to insert them into the MSSQL Accounting System.
   * Only after the accounting system confirms it has successfully saved the data, the Python script sends a command to your MySQL database: UPDATE msp
     SET status = 'success' ....
   * Therefore, seeing "success" in your database is the confirmation that the data has safely reached the accounting system.


  2. Does the accounting system just "view" the data?
  Yes, for these specific transactions, the accounting system treats them as "Finalized" upon entry.
  Because your script inserts the data with high-level protection flags:
   * `certis = 3`: This tells the accounting system that the record is already Approved/Posted.
   * `lock = 4`: This tells the system that the record is Locked.


  The Result:
  When an accountant opens the APIS Accounting System (the VB.NET application), they will see these transactions in their reports (General Ledger,
  Balance Sheet, etc.) as if they had manually entered and posted them themselves. They generally do not need to perform any further updates like
  "Confirming" or "Posting" because your Python script has already done that "heavy lifting" for them.


  In summary:
   * Your Python Service: Is the "Worker" that does the entry and the status update.
   * APIS Accounting System: Is the "Storehouse" that holds the records for viewing, reporting, and auditing. No further action is required from the
     accountants for these records to be considered complete.
