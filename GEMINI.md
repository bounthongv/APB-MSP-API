# Project Context: APB API (TaxAPI)

## Project Overview
This project is a Flask-based Web API designed for expense management and utility services. It interacts with a Microsoft SQL Server (MSSQL) database to store and retrieve expense records. Key features include:
- **Expense Management:** Uploading, cancelling, searching, and retrieving expense records via the `/msp` endpoints.
- **Utility:** A specialized endpoint for converting numbers to their Lao word representation.
- **Security:** Implements Bearer Token authentication and a custom signature verification mechanism for data integrity.

## Tech Stack
- **Language:** Python
- **Framework:** Flask
- **Database:** Microsoft SQL Server (MSSQL)
- **Driver:** `pyodbc` (ODBC Driver 17 for SQL Server)
- **Server:** Waitress (listed in requirements) or built-in Flask server for dev.

## Key Files & Structure
- **`api.py`**: The main entry point of the application. It initializes the Flask app, defines utility endpoints (`/number-to-words`, `/ping`), and registers the `msp_api` blueprint.
- **`msp_api.py`**: A Flask Blueprint (`msp_bp`) containing all expense-related business logic and endpoints (`/msp/upload`, `/msp/getStatus`, etc.).
- **`shared_utils.py`**: (Inferred) Contains shared helper functions for database connections (`get_db_connection`), authentication (`token_required`), and signature generation (`generate_signature`).
- **`dbConnect.py`**: A utility script to test the connectivity to the MSSQL database.
- **`requirements.txt`**: Lists the project dependencies.

## Setup & Installation

1.  **Prerequisites:**
    - Python 3.x
    - ODBC Driver 17 for SQL Server installed on the system.

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration:**
    Create a `.env` file (or set environment variables) with the following keys (defaults shown):
    - `DB_HOST`: Database host (default: `localhost\MSSQLSERVER`)
    - `DB_PORT`: Database port (default: `1558`)
    - `DB_USER`: Database user (default: `APIS_TEST`)
    - `DB_PASSWORD`: Database password
    - `DB_NAME`: Database name (default: `TaxAPI`)
    - `API_TOKEN` or `BEARER_TOKEN`: Token for `Bearer` authentication.

## Running the Application

**Development Mode:**
To run the application using the built-in Flask server (debug mode enabled):
```bash
python api.py
```
The server will start on `http://0.0.0.0:5000`.

**Database Connection Test:**
To verify the database connection:
```bash
python dbConnect.py
```

## API Endpoints

### Utility
- `GET /`: Returns API status.
- `GET /ping`: Returns "alive".
- `POST /number-to-words`: Converts a numeric input to Lao words. Requires Bearer Token.

### Expense Management (`/msp`)
All `/msp` endpoints require Bearer Token and Custom Signature authentication.
- `POST /msp/upload`: Upload a new expense record (inserts into `expense`, `tbl_dr`, `tbl_cr`).
- `POST /msp/getStatus`: Check the status of an expense by `exp_no`.
- `PATCH /msp/cancel`: Cancel an expense (only if status is 'wait' or 'success').
- `POST /msp/searchByDate`: Search for expenses within a date range.
- `GET /msp/retrieve`: Retrieve all expenses matching a specific status.

## Development Conventions
- **Blueprints:** The project uses Flask Blueprints to organize routes (e.g., `msp_api` for expense logic).
- **Authentication:**
    - Routes are protected by a `@token_required` decorator.
    - Business logic endpoints enforce a custom `generate_signature` check using `keyCode`, `signDate`, and a transaction identifier (like `exp_no` or `request_no`).
- **Database:** Uses `pyodbc` with raw SQL queries. Transactions are managed explicitly (commit/rollback).
