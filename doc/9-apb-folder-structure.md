# APB API — Ubuntu Server Folder Structure

Both services are deployed under `/root/` on the Ubuntu server, running as `root`.

## Directory Layout

```
/root/
├── apb_api/                          ← Flask API (web service)
│   ├── api.py                        Entry point — registers blueprints, runs waitress
│   ├── msp_api.py                    Blueprint — /msp/* expense endpoints
│   ├── apis_api.py                   Blueprint — /apis/* retrieve endpoints
│   ├── shared_utils.py               DB connection, token auth, signature helpers
│   ├── generate_signature.py         Standalone signature generator
│   ├── test_db.py                    DB connectivity test
│   ├── .env                          Environment config (DB creds, tokens)
│   ├── venv/                         Python virtual environment
│   ├── requirements.txt
│   └── (other files...)
│
├── cron_sync/                        ← Sync service (polling loop)
│   ├── apb_sync                      Compiled PyInstaller one-file binary
│   ├── .env                          MSSQL & MySQL connection config
│   └── (no source — runs from compiled binary)
│
└── ... (other project files)
```

## systemd Services

### 1. Flask API (`apb_api.service`)

| Setting | Value |
|---|---|
| Description | APB API Service |
| User | root |
| WorkingDirectory | `/root/apb_api` |
| ExecStart | `/root/apb_api/venv/bin/python -m waitress --listen=*:8000 api:app` |
| Restart | always |

The Flask app runs behind **Waitress** on port **8000**. It serves the `/msp/upload`, `/msp/getStatus`, `/msp/cancel`, `/msp/searchByDate`, `/msp/retrieve`, `/apis/retrieve_msp_status`, `/apis/retrieve_msp_trn_id`, and `/number-to-words` endpoints. Reads its `.env` from `/root/apb_api/.env`.

### 2. Sync Service (`apb_sync.service`)

| Setting | Value |
|---|---|
| Description | APB Sync Service (MSP Sync) |
| User | root |
| WorkingDirectory | `/root/cron_sync` |
| ExecStart | `/root/cron_sync/apb_sync` |
| Restart | always |
| RestartSec | 60 seconds |

The sync service runs as a **compiled binary** (`apb_sync`, PyInstaller one-file). It reads `.env` from `/root/cron_sync/.env`. Since `Restart=always` with `RestartSec=60`, systemd keeps it in a continuous loop:

1. Run `apb_sync` (connects MySQL → MSSQL, pushes pending 'wait' records, processes cancellations)
2. Exit (finished one cycle)
3. systemd waits 60 seconds
4. Restart → back to step 1

### Service Management Commands

```bash
# API service
sudo systemctl restart apb_api
sudo systemctl status apb_api
sudo journalctl -u apb_api -f

# Sync service
sudo systemctl restart apb_sync
sudo systemctl status apb_sync
sudo journalctl -u apb_sync -f
```

## Environment Files

Both services have their own `.env`:

- **`/root/apb_api/.env`** — Local MySQL connection, API bearer token
- **`/root/cron_sync/.env`** — Local MySQL + remote MSSQL connection configs
