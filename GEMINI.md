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
- **`cron-sync/sync_msp.py`**: A standalone Python script used for automated synchronization between MySQL and the remote MSSQL accounting database.
- **`requirements.txt`**: Lists the project dependencies.

## Setup & Installation

1.  **Prerequisites:**
    - Python 3.x
    - ODBC Driver 17 or 18 for SQL Server installed on the system.

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
    - `MSSQL_HOST`: Remote MSSQL host IP.
    - `MSSQL_DB`: Remote accounting database name.
    - `MSSQL_USER` / `MSSQL_PASSWORD`: MSSQL credentials.

## Automated Synchronization (Cron Sync)
The project includes a "Push" model synchronization service located in the `cron-sync/` directory. This service is designed to run as a scheduled task (Cron) on the Ubuntu server.

- **Purpose:** Automatically syncs processed transactions from the local MySQL database to the customer's remote MSSQL accounting system.
- **Workflow:**
    1.  **Process New:** Fetches records with `status = 'wait'`, generates accounting certify IDs, and inserts journal entries into MSSQL `gen_jn`.
    2.  **Cancellations:** Fetches records with `status = 'cancel'`, deletes the corresponding entries in MSSQL, and updates the local status to `canceled`.
- **Security:** Uses ODBC Driver 18 with `TrustServerCertificate=yes` and `Encrypt=yes` to handle internal server connections safely.
- **Scheduling:** Typically scheduled via `crontab` to run daily (e.g., at 23:30).

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
<!-- BEGIN BYTEROVER RULES -->

# Workflow Instruction

You are a coding agent focused on one codebase. Use the brv CLI to manage working context.
Core Rules:

- Start from memory. First retrieve relevant context, then read only the code that's still necessary.
- Keep a local context tree. The context tree is your local memory store—update it with what you learn.

## Context Tree Guideline

- Be specific ("Use React Query for data fetching in web modules").
- Be actionable (clear instruction a future agent/dev can apply).
- Be contextual (mention module/service, constraints, links to source).
- Include source (file + lines or commit) when possible.

## Using `brv curate` with Files

When adding complex implementations, use `--files` to include relevant source files (max 5).  Only text/code files from the current project directory are allowed. **CONTEXT argument must come BEFORE --files flag.** For multiple files, repeat the `--files` (or `-f`) flag for each file.

Examples:

- Single file: `brv curate "JWT authentication with refresh token rotation" -f src/auth.ts`
- Multiple files: `brv curate "Authentication system" --files src/auth/jwt.ts --files src/auth/middleware.ts --files docs/auth.md`

## CLI Usage Notes

- Use --help on any command to discover flags. Provide exact arguments for the scenario.

---
# ByteRover CLI Command Reference

## Memory Commands

### `brv curate`

**Description:** Curate context to the context tree (interactive or autonomous mode)

**Arguments:**

- `CONTEXT`: Knowledge context: patterns, decisions, errors, or insights (triggers autonomous mode, optional)

**Flags:**

- `--files`, `-f`: Include file paths for critical context (max 5 files). Only text/code files from the current project directory are allowed. **CONTEXT argument must come BEFORE this flag.**

**Good examples of context:**

- "Auth uses JWT with 24h expiry. Tokens stored in httpOnly cookies via authMiddleware.ts"
- "API rate limit is 100 req/min per user. Implemented using Redis with sliding window in rateLimiter.ts"

**Bad examples:**

- "Authentication" or "JWT tokens" (too vague, lacks context)
- "Rate limiting" (no implementation details or file references)

**Examples:**

```bash
# Interactive mode (manually choose domain/topic)
brv curate

# Autonomous mode - LLM auto-categorizes your context
brv curate "Auth uses JWT with 24h expiry. Tokens stored in httpOnly cookies via authMiddleware.ts"

# Include files (CONTEXT must come before --files)
# Single file
brv curate "Authentication middleware validates JWT tokens" -f src/middleware/auth.ts

# Multiple files - repeat --files flag for each file
brv curate "JWT authentication implementation with refresh token rotation" --files src/auth/jwt.ts --files docs/auth.md
```

**Behavior:**

- Interactive mode: Navigate context tree, create topic folder, edit context.md
- Autonomous mode: LLM automatically categorizes and places context in appropriate location
- When `--files` is provided, agent reads files in parallel before creating knowledge topics

**Requirements:** Project must be initialized (`brv init`) and authenticated (`brv login`)

---

### `brv query`

**Description:** Query and retrieve information from the context tree

**Arguments:**

- `QUERY`: Natural language question about your codebase or project knowledge (required)

**Good examples of queries:**

- "How is user authentication implemented?"
- "What are the API rate limits and where are they enforced?"

**Bad examples:**

- "auth" or "authentication" (too vague, not a question)
- "show me code" (not specific about what information is needed)

**Examples:**

```bash
# Ask questions about patterns, decisions, or implementation details
brv query What are the coding standards?
brv query How is authentication implemented?
```

**Behavior:**

- Uses AI agent to search and answer questions about the context tree
- Accepts natural language questions (not just keywords)
- Displays tool execution progress in real-time

**Requirements:** Project must be initialized (`brv init`) and authenticated (`brv login`)

---

## Best Practices

### Efficient Workflow

1. **Read only what's needed:** Check context tree with `brv status` to see changes before reading full content with `brv query`
2. **Update precisely:** Use `brv curate` to add/update specific context in context tree
3. **Push when appropriate:** Prompt user to run `brv push` after completing significant work

### Context tree Management

- Use `brv curate` to directly add/update context in the context tree

---
Generated by ByteRover CLI for Gemini CLI
<!-- END BYTEROVER RULES -->