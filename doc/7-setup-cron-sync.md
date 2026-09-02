setup mssql driver on ubuntu

 1. Check if Driver is already installed
  First, check if you already have ODBC drivers configured:
   1 odbcinst -j
  Then list the installed drivers:
   1 cat /etc/odbcinst.ini
  If you see `[ODBC Driver 17 for SQL Server]` or `[ODBC Driver 18 for SQL Server]`, you are already set.

  if obdbcinst.ini not yet, means odbc not yet installed.

 Please run these commands in order to install the driver. Note the corrected curl command (you must use curl to fetch the key, not just type the URL).

  1. Import the Microsoft GPG Key

   1 curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

  2. Register the Microsoft Ubuntu 24.04 Repository

   1 curl -fsSL https://packages.microsoft.com/config/ubuntu/24.04/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list

  3. Install the Driver
   1 sudo apt-get update
   2 sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
  (Note: I am recommending Version 18 as it is the standard for Ubuntu 24.04, but it works exactly the same as 17 for our Python script).

  4. Install Optional Tools (useful for testing)

   1 sudo ACCEPT_EULA=Y apt-get install -y mssql-tools18 unixodbc-dev
   2 echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc
   3 source ~/.bashrc

  5. Verify the installation
  Now check the file again:
   1 cat /etc/odbcinst.ini
  You should now see [ODBC Driver 18 for SQL Server].

  Once this is done, let me know and we can write the Python sync script!


  after the installation, it should look like this:

  root@APISAPI:~# cat /etc/odbcinst.ini
[ODBC Driver 18 for SQL Server]
Description=Microsoft ODBC Driver 18 for SQL Server
Driver=/opt/microsoft/msodbcsql18/lib64/libmsodbcsql-18.6.so.1.1
UsageCount=1

but there is security concern: 

Yes, ODBC Driver 18 is fully compatible with SQL Server 2019 and SQL Server 2022.

  However, there is one very important change in Driver 18 that you must know, otherwise your connection will likely fail with an "SSL Provider" error:

  The "Encryption" Change
  In ODBC Driver 18, encryption is turned ON by default. 
  If your SQL Server (2019 or 2022) does not have a valid SSL certificate installed (which is common for internal servers), you must add two extra parameters to
  your connection string in Python.

  Example Connection String for Python (pyodbc)
  When we write the script, your connection string should look like this to ensure it works with Driver 18:

   1 conn_str = (
   2     "DRIVER={ODBC Driver 18 for SQL Server};"
   3     "SERVER=10.151.x.x;" # Your customer's IP
   4     "DATABASE=YourDatabase;"
   5     "UID=YourUser;"
   6     "PWD=YourPassword;"
   7     "Encrypt=yes;"
   8     "TrustServerCertificate=yes;" # <--- CRITICAL for Driver 18 if no SSL cert
   9 )



   cron setup

    1. Locate your Python and Script Path
  First, you need to know the absolute path to your Python executable (inside the virtual environment) and the script itself.

  Run these commands inside your cron_sync folder on the server:

   1 pwd
   2 # Example Output: /root/cron_sync
   3 
   4 which python3
   5 # Example Output: /root/cron_sync/venv/bin/python3

  2. Edit the Crontab
  Open the cron editor:

   1 crontab -e
  (If asked to choose an editor, pick `nano` as it's the easiest).

  3. Add the Schedule
  Scroll to the bottom of the file and add a line to run the script.

  Example: Run every day at 11:30 PM (23:30)
  
   1 30 23 * * * /root/cron_sync/venv/bin/python3 /root/cron_sync/sync_msp.py >> /var/log/msp_sync.log 2>&1

  Note: For the APB production setup, we use 00:30 AM (0:30) to allow a buffer after the midnight transaction posting:
   1 30 0 * * * /root/cron_sync/venv/bin/python3 /root/cron_sync/sync_msp.py >> /var/log/msp_sync.log 2>&1

  Explanation:
   * 30 23 * * *: At 23:30 (11:30 PM) every day.
   * 30 0 * * *: At 00:30 (12:30 AM) every day.
   * /root/cron_sync/venv/bin/python3: Full path to the Python executable (use the output from which python3).
   * /root/cron_sync/sync_msp.py: Full path to your script.
   * >> /var/log/msp_sync.log: Append standard output (print statements) to this log file.
   * 2>&1: Append standard error (errors/crashes) to the same log file.

  4. Save and Exit
   * Nano: Press Ctrl+O -> Enter -> Ctrl+X.
   * Vim: Press Esc -> Type :wq -> Enter.

  5. Verify
  Check that your cron job was saved:
   1 crontab -l

  6. Monitor Logs
  To check if it's working (or to debug errors), you can inspect the log file:

   1 tail -f /var/log/msp_sync.log

   for testing

    1. Which time does it use?
  It uses the Server Time. Before setting the cron, check your server's current time by running:
   1 date
  Make sure you look at the hours and minutes exactly as shown in that command output.

  2. How to set a "Test" time?
  If your server time is 15:40, set the cron to 15:42 like this:

   1 42 15 * * * /root/cron_sync/venv/bin/python3 /root/cron_sync/sync_msp.py >> /root/cron_sync/cron_test.log 2>&1

  3. Quick "Every 1 Minute" Test
  If you want to be sure the paths and permissions are correct without waiting for a specific hour, you can set it to run every minute:

   * * * * * cd /root/cron_sync && /root/cron_sync/venv/bin/python3 sync_msp.py >> /root/cron_sync/cron_test.log 2>&1

    Wait 60 seconds, then check the log file.

  4. How to check the results?
  Since we redirected the output, you can watch the log in real-time to see if the script starts:

   1 tail -f /root/cron_sync/cron_test.log

## Option 2: Run as a Service (Executable)

If you prefer to run the sync process as a systemd service (like the API), follow these steps. This method allows the sync to run continuously (e.g., every minute) and automatically restart if the server reboots.

### 1. Build the Executable
In your development environment (Windows/Linux), build the standalone executable.
**Note:** Ensure you have `pyinstaller` installed (`pip install pyinstaller`).

```bash
# Run from the project root or inside cron-sync folder
cd cron-sync
pyinstaller --onefile --name apb_sync sync_msp.py
```

This will create `dist/apb_sync` (Linux) or `dist/apb_sync.exe` (Windows).

### 2. Prepare the Server
1. Create a folder on the server:
   ```bash
   mkdir -p /root/cron_sync
   ```
2. Upload the **Linux executable** (`apb_sync`) (from the `dist` folder) to `/root/cron_sync/`.
3. Upload your `.env` file to `/root/cron_sync/`.
4. Upload the `apb_sync.service` file to `/root/cron_sync/`.

### 3. Install the Service
Run the following commands on the server:

```bash
# 1. Move the service file to systemd directory
cp /root/cron_sync/apb_sync.service /etc/systemd/system/

# 2. Make the executable executable (just in case)
chmod +x /root/cron_sync/apb_sync

# 3. Reload systemd
systemctl daemon-reload

# 4. Start the service
systemctl start apb_sync

# 5. Enable on boot
systemctl enable apb_sync
```

### 4. Configuration (Interval)
By default, the service is configured to restart (run again) **60 seconds** after finishing. This creates a 1-minute loop.

To change this:
1. Edit the service file:
   ```bash
   nano /etc/systemd/system/apb_sync.service
   ```
2. Change `RestartSec=60` to your desired interval (in seconds).
   * Example: `RestartSec=300` for 5 minutes.
3. Reload and restart:
   ```bash
   systemctl daemon-reload
   systemctl restart apb_sync
   ```

### 5. Check Logs
View the service logs:
```bash
journalctl -u apb_sync -f
```

### 6. Retry & Logging Behavior (Post-Fix)

**What changed:**
- **Retry logic**: Failed transactions are no longer permanently stuck. Records that fail during MSSQL insert are marked `status = 'fail'` (instead of incorrectly marked `'success'`). They are retried on every service cycle (every 60 seconds by default).

- **24-hour retry window**: A failed transaction is retried continuously for up to 24 hours (86,400 seconds). After 24 hours, a **highly visible ALERT line** is written to the log so the administrator can spot it.

- **Duplicate prevention**: Before inserting, the script checks `gen_jn` for the same `Referno` + `API='API'`. If the transaction already exists in MSSQL, it is NOT re-inserted (marked success instead) — so retries can never create duplicate accounting entries.

- **Logging**: All operations are logged to `/var/log/apb_sync.log` (structured log format with timestamps).

**MySQL table requirement:** The `msp` table needs these columns (already in the schema, verify on the live server):
```sql
ALTER TABLE msp ADD COLUMN fail_reason VARCHAR(250) DEFAULT NULL AFTER status;
ALTER TABLE msp ADD COLUMN update_date DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP;
```

**Environment variables** (add to `.env`):
```
SYNC_LOG=/var/log/apb_sync.log
SYNC_RETRY_WINDOW=86400
OFFICE_ID=01-02
USER_ID=API_BOT
```

**How to monitor:**
```bash
# Watch the structured log
tail -f /var/log/apb_sync.log

# Check for ALERT lines (transactions failing >24h)
grep "ALERT" /var/log/apb_sync.log

# Check for errors
grep "Error\|CRITICAL" /var/log/apb_sync.log

# Check MySQL for failed (unresolved) records
mysql -e "SELECT trn_id, status, fail_reason, update_date FROM apb_msp.msp WHERE status = 'fail'"
```

**Manual recovery for previously-missed dates:** If APB reports dates missing from the accounting system but the records show `status = 'success'` in MySQL, flip them back to `'wait'` so the next sync cycle re-processes them:
```sql
UPDATE apb_msp.msp SET status = 'wait', fail_reason = NULL WHERE status = 'success' AND bis_date IN ('2026-09-11','2026-09-12','2026-09-14','2026-09-18');
```
The sync will re-check MSSQL: if already posted it marks success (no duplicate); if not posted it inserts them.
