# APIS Integration API

This document details the API endpoints specifically designed for the **APIS Accounting System** (VB.NET .NET 3.5) to interact with the **MSP** database.

**Base URL:** `http://<YOUR_UBUNTU_SERVER_IP>:8000/apis`
**Authentication:** All endpoints require a `Bearer Token` header.

---

## 1. API Endpoints

### A. Retrieve Transactions by Status
Fetches a list of MSP transactions based on their current status (e.g., 'wait', 'cancel').

*   **Endpoint:** `GET /retrieve_msp_status`
*   **Parameters:** `status` (Query String or JSON Body)
*   **Description:** Use this to start your batch process.
    *   `status=wait`: To find new transactions to post.
    *   `status=cancel`: To find transactions that need reversal.

### B. Retrieve Transaction Details
Fetches a single MSP transaction record by its ID.

*   **Endpoint:** `GET /retrieve_msp_trn_id`
*   **Parameters:** `trn_id` (Query String or JSON Body)
*   **Description:** Useful for verification or re-fetching a specific item.

### C. Retrieve Debit/Credit Entries
Fetches the accounting lines associated with a transaction.

*   **Endpoint:** `GET /retrieve_dr_trn_id`
*   **Endpoint:** `GET /retrieve_cr_trn_id`
*   **Parameters:** `trn_id` (Query String or JSON Body)
*   **Description:** Returns the rows from `tbl_dr` or `tbl_cr` needed to construct the accounting journal.

### D. Update Status (General)
Updates the status of a transaction.

*   **Endpoint:** `PATCH /update_status`
*   **Payload (JSON):**
    ```json
    {
      "trn_id": "TRANS-001",
      "status": "success",
      "fail_reason": "Optional error message"
    }
    ```
*   **Description:** Call this after successfully posting to MSSQL (to mark as 'success') or if validation fails (to mark as 'fail').

### E. Confirm Cancellation
Safely transitions a record from `cancel` to `canceled`.

*   **Endpoint:** `PATCH /confirm_cancel`
*   **Payload (JSON):** `{"trn_id": "TRANS-001"}`
*   **Description:** Call this **only** after successfully reversing the accounting entry in MSSQL. It enforces that the current status is `cancel` before updating.

---

## 2. VB.NET Implementation Workflow

The key to a reliable integration is the **"Check Local First" (Idempotency)** pattern. This prevents duplicate entries if the network fails between the MSSQL insert and the API update.

### Recommended Workflow

#### Scenario A: Processing New Transactions ('wait')

1.  **Fetch Batch:** Call `GET /retrieve_msp_status?status=wait`.
2.  **Loop** through each transaction in the result.
3.  **Check Local MSSQL:**
    *   Query your APIS database: `SELECT COUNT(*) FROM VoucherTable WHERE RefID = @trn_id`
4.  **Logic:**
    *   **If Exists:** The record was already processed but the status update failed previously.
        *   **Action:** Do NOT insert. Call `PATCH /update_status` (set to 'success') immediately.
    *   **If NOT Exists:** This is a new record.
        *   **Action:**
            1.  Call `GET /retrieve_dr_trn_id` & `GET /retrieve_cr_trn_id`.
            2.  Insert into MSSQL (Begin Transaction -> Insert -> Commit).
            3.  If MSSQL Success: Call `PATCH /update_status` (set to 'success').
            4.  If MSSQL Fail: Log error locally.

#### Scenario B: Processing Cancellations ('cancel')

1.  **Fetch Batch:** Call `GET /retrieve_msp_status?status=cancel`.
2.  **Loop** through each transaction.
3.  **Check Local MSSQL:** Verify the original voucher exists and is not already reversed.
4.  **Action:**
    1.  Create Reversal Entry in MSSQL.
    2.  If MSSQL Success: Call `PATCH /confirm_cancel`.

---

## 3. VB.NET Code Sample (.NET 3.5)

**Prerequisites:**
1.  Add Reference: `Newtonsoft.Json.dll` (.NET 3.5 version).
2.  Add Reference: `System.Data`.

### `ApiService.vb` Module

```vb
Imports System.Net
Imports System.Data
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Linq

Public Class ApiService
    ' Configuration
    Private Const BaseUrl As String = "http://<YOUR_UBUNTU_IP>:8000/apis"
    Private Const ApiToken As String = "<YOUR_TOKEN>"

    ' --- Helper to setup WebClient with Headers ---
    Private Shared Function CreateClient() As WebClient
        Dim client As New WebClient()
        client.Encoding = System.Text.Encoding.UTF8
        client.Headers.Add("Authorization", "Bearer " & ApiToken)
        client.Headers.Add("Content-Type", "application/json")
        Return client
    End Function

    ' --- 1. Fetch MSP Records (Returns DataTable) ---
    Public Shared Function GetMspData(ByVal status As String) As DataTable
        Dim url As String = BaseUrl & "/retrieve_msp_status?status=" & status
        Dim dt As New DataTable()

        Using client As CreateClient()
            Try
                Dim jsonResponse As String = client.DownloadString(url)
                Dim rootObject As JObject = JObject.Parse(jsonResponse)
                
                ' Check response code
                If rootObject("code").ToString() <> "200" Then Throw New Exception(rootObject("message").ToString())

                Dim dataRows As JArray = CType(rootObject("data"), JArray)
                dt = JsonConvert.DeserializeObject(Of DataTable)(dataRows.ToString())
            Catch ex As Exception
                Console.WriteLine("GetMspData Error: " & ex.Message)
                Return Nothing
            End Try
        End Using
        Return dt
    End Function

    ' --- 2. Fetch Debit/Credit Details ---
    Public Shared Function GetDetails(ByVal endpoint As String, ByVal trnId As String) As DataTable
        Dim url As String = BaseUrl & "/" & endpoint & "?trn_id=" & trnId
        Dim dt As New DataTable()

        Using client As CreateClient()
            Try
                Dim jsonResponse As String = client.DownloadString(url)
                Dim rootObject As JObject = JObject.Parse(jsonResponse)
                
                If rootObject("code").ToString() <> "200" Then Return Nothing ' Handle 404/Empty

                Dim dataRows As JArray = CType(rootObject("data"), JArray)
                dt = JsonConvert.DeserializeObject(Of DataTable)(dataRows.ToString())
            Catch ex As Exception
                Console.WriteLine("GetDetails Error: " & ex.Message)
                Return Nothing
            End Try
        End Using
        Return dt
    End Function

    ' --- 3. Update Status (Success/Fail) ---
    Public Shared Function UpdateStatus(ByVal trnId As String, ByVal newStatus As String, Optional ByVal failReason As String = "") As Boolean
        Dim url As String = BaseUrl & "/update_status"
        
        Using client As CreateClient()
            Dim payload As New JObject()
            payload.Add("trn_id", trnId)
            payload.Add("status", newStatus)
            If failReason <> "" Then payload.Add("fail_reason", failReason)

            Try
                ' WebClient UploadString defaults to POST. 
                ' If server strictly requires PATCH, use "PATCH" as second arg.
                client.UploadString(url, "PATCH", payload.ToString())
                Return True
            Catch ex As Exception
                Console.WriteLine("UpdateStatus Error: " & ex.Message)
                Return False
            End Try
        End Using
    End Function

    ' --- 4. Confirm Cancel ---
    Public Shared Function ConfirmCancel(ByVal trnId As String) As Boolean
        Dim url As String = BaseUrl & "/confirm_cancel"
        
        Using client As CreateClient()
            Dim payload As New JObject()
            payload.Add("trn_id", trnId)

            Try
                client.UploadString(url, "PATCH", payload.ToString())
                Return True
            Catch ex As Exception
                Console.WriteLine("ConfirmCancel Error: " & ex.Message)
                Return False
            End Try
        End Using
    End Function

End Class
```

### Main Logic Example (Form Button Click)

```vb
Private Sub btnProcessWait_Click(sender As Object, e As EventArgs) Handles btnProcessWait.Click
    ' 1. Get Pending Transactions
    Dim dtWait As DataTable = ApiService.GetMspData("wait")

    If dtWait Is Nothing OrElse dtWait.Rows.Count = 0 Then
        MsgBox("No pending transactions.")
        Exit Sub
    End If

    ' 2. Loop through each record
    For Each row As DataRow In dtWait.Rows
        Dim trnId As String = row("trn_id").ToString()
        
        ' --- A. IDEMPOTENCY CHECK (CRITICAL) ---
        ' Check if we already have this trn_id in our local MSSQL
        If LocalDatabase.Exists(trnId) Then
            ' Already done locally, just fix the API status
            ApiService.UpdateStatus(trnId, "success")
            Continue For
        End If

        ' --- B. Fetch Details ---
        Dim dtDr As DataTable = ApiService.GetDetails("retrieve_dr_trn_id", trnId)
        Dim dtCr As DataTable = ApiService.GetDetails("retrieve_cr_trn_id", trnId)

        ' --- C. Perform Accounting (MSSQL) ---
        Dim success As Boolean = LocalDatabase.InsertVoucher(row, dtDr, dtCr)

        ' --- D. Update API Status ---
        If success Then
            ApiService.UpdateStatus(trnId, "success")
        Else
            ' Optional: Mark as failed or leave as wait to retry
            ApiService.UpdateStatus(trnId, "fail", "MSSQL Insert Error")
        End If
    Next
    
    MsgBox("Batch processing complete.")
End Sub
```

---

## 4. Optional Solution: Staging Tables (ETL Approach)

This approach is recommended if your team prefers handling complex logic in **SQL Stored Procedures** rather than VB.NET code. It involves fetching data from the API and dumping it directly into temporary "Staging Tables" in your MSSQL database.

**Benefit:** Easier debugging (you can see the raw data in SQL tables) and cleaner VB.NET code.

### Step 1: Create Staging Tables in MSSQL

Execute this SQL script once to create the necessary tables.

```sql
-- 1. Main Transaction Staging Table
CREATE TABLE STAGE_MSP (
    trn_id NVARCHAR(50) NOT NULL PRIMARY KEY,
    trn_desc NVARCHAR(255),
    currency NVARCHAR(10),
    acc_book NVARCHAR(50),
    status NVARCHAR(20),
    fail_reason NVARCHAR(255),
    bis_date DATETIME,
    create_date DATETIME,
    update_date DATETIME,
    ex_rate DECIMAL(18, 4)
);

-- 2. Debit Staging Table
CREATE TABLE STAGE_TBL_DR (
    id INT IDENTITY(1,1) PRIMARY KEY,
    trn_id NVARCHAR(50) NOT NULL,
    dr_ac NVARCHAR(50),
    dr_amt DECIMAL(18, 2),
    dr_amt_lak DECIMAL(18, 2),
    dr_desc NVARCHAR(255)
);
CREATE INDEX IX_STAGE_DR_TRN ON STAGE_TBL_DR(trn_id);

-- 3. Credit Staging Table
CREATE TABLE STAGE_TBL_CR (
    id INT IDENTITY(1,1) PRIMARY KEY,
    trn_id NVARCHAR(50) NOT NULL,
    cr_ac NVARCHAR(50),
    cr_amt DECIMAL(18, 2),
    cr_amt_lak DECIMAL(18, 2),
    cr_desc NVARCHAR(255)
);
CREATE INDEX IX_STAGE_CR_TRN ON STAGE_TBL_CR(trn_id);
```

### Step 2: VB.NET Code to Load Staging Tables

This module clears the old data and inserts the new batch from the API.

```vb
Imports System.Data.SqlClient

Public Class StagingService

    Private Const ConnectionString As String = "Data Source=YOUR_SERVER;Initial Catalog=YOUR_DB;User ID=user;Password=pass"

    ''' <summary>
    ''' Fetches 'wait' transactions from API and inserts them into MSSQL STAGE tables.
    ''' </summary>
    Public Shared Sub LoadStagingData()
        ' 1. Fetch Header Data from API
        Dim dtMsp As DataTable = ApiService.GetMspData("wait")
        
        If dtMsp Is Nothing OrElse dtMsp.Rows.Count = 0 Then
            Console.WriteLine("No pending data found.")
            Exit Sub
        End If

        Using conn As New SqlConnection(ConnectionString)
            conn.Open()

            ' 2. Clear Old Staging Data
            Dim cmdClear As New SqlCommand("DELETE FROM STAGE_MSP; DELETE FROM STAGE_TBL_DR; DELETE FROM STAGE_TBL_CR;", conn)
            cmdClear.ExecuteNonQuery()

            ' 3. Iterate and Insert
            For Each row As DataRow In dtMsp.Rows
                Dim trnId As String = row("trn_id").ToString()

                ' --- Insert Header (STAGE_MSP) ---
                Dim queryMsp As String = "INSERT INTO STAGE_MSP (trn_id, trn_desc, currency, acc_book, status, bis_date, create_date, ex_rate) " & _
                                         "VALUES (@id, @desc, @curr, @book, @stat, @bis, @create, @rate)"
                
                Using cmd As New SqlCommand(queryMsp, conn)
                    cmd.Parameters.AddWithValue("@id", trnId)
                    cmd.Parameters.AddWithValue("@desc", row("trn_desc"))
                    cmd.Parameters.AddWithValue("@curr", row("currency"))
                    cmd.Parameters.AddWithValue("@book", row("acc_book"))
                    cmd.Parameters.AddWithValue("@stat", row("status"))
                    cmd.Parameters.AddWithValue("@bis", row("bis_date"))
                    cmd.Parameters.AddWithValue("@create", row("create_date"))
                    cmd.Parameters.AddWithValue("@rate", row("ex_rate"))
                    cmd.ExecuteNonQuery()
                End Using

                ' --- Fetch & Insert Debits ---
                Dim dtDr As DataTable = ApiService.GetDetails("retrieve_dr_trn_id", trnId)
                If dtDr IsNot Nothing Then
                    For Each drRow As DataRow In dtDr.Rows
                        Dim queryDr As String = "INSERT INTO STAGE_TBL_DR (trn_id, dr_ac, dr_amt, dr_amt_lak, dr_desc) " & _
                                                "VALUES (@id, @ac, @amt, @lak, @desc)"
                        Using cmdDr As New SqlCommand(queryDr, conn)
                            cmdDr.Parameters.AddWithValue("@id", trnId)
                            cmdDr.Parameters.AddWithValue("@ac", drRow("dr_ac"))
                            cmdDr.Parameters.AddWithValue("@amt", drRow("dr_amt"))
                            cmdDr.Parameters.AddWithValue("@lak", drRow("dr_amt_lak"))
                            cmdDr.Parameters.AddWithValue("@desc", drRow("dr_desc"))
                            cmdDr.ExecuteNonQuery()
                        End Using
                    Next
                End If

                ' --- Fetch & Insert Credits ---
                Dim dtCr As DataTable = ApiService.GetDetails("retrieve_cr_trn_id", trnId)
                If dtCr IsNot Nothing Then
                    For Each crRow As DataRow In dtCr.Rows
                        Dim queryCr As String = "INSERT INTO STAGE_TBL_CR (trn_id, cr_ac, cr_amt, cr_amt_lak, cr_desc) " & _
                                                "VALUES (@id, @ac, @amt, @lak, @desc)"
                        Using cmdCr As New SqlCommand(queryCr, conn)
                            cmdCr.Parameters.AddWithValue("@id", trnId)
                            cmdCr.Parameters.AddWithValue("@ac", crRow("cr_ac"))
                            cmdCr.Parameters.AddWithValue("@amt", crRow("cr_amt"))
                            cmdCr.Parameters.AddWithValue("@lak", crRow("cr_amt_lak"))
                            cmdCr.Parameters.AddWithValue("@desc", crRow("cr_desc"))
                            cmdCr.ExecuteNonQuery()
                        End Using
                    Next
                End If

            Next
        End Using

        Console.WriteLine("Staging Load Complete.")
    End Sub

End Class
```

### Step 3: Processing (SQL Stored Procedure)

After running `LoadStagingData()`, your workflow is simple:
1.  Call your custom Stored Procedure (e.g., `sp_Process_From_Stage`).
    *   This SP reads from `STAGE_...` tables and inserts into your real accounting tables.
    *   Crucially, it should **return the list of trn_ids** that were successfully processed.
2.  Loop through that list in VB.NET and call `ApiService.UpdateStatus(id, "success")`.