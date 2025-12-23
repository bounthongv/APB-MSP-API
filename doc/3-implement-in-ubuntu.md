since I have code develop in windows need to:
1. create folder for msp api: (/home/apis/apb_api)
cd apb_api
python3 -version
sudo apt update
python3 -m venv venv
source venv/bin/activate

   1 sudo chown -R apis:apis ~/apb_api/venv
   2 pip install -r requirements.txt


2. create virtual environment for msp api: (sudo nano .env)
API_TOKEN=8c57a7c3dfe7307abf40c9e35d0508ba6d2e2c4dda27ae66567627b0da5d68ae
DB_HOST=localhost
DB_USER=admin
DB_PASSWORD=Sql_admin@#2024
DB_NAME=apb_msp


running python test first

run test db first
python test_db.py in another terminal

(venv) apis@apissrv:~/apb_api$ python test_db.py
Attempting to connect to host: localhost
Using database user: admin
Connecting to database...
Successfully connected to the database!
/home/apis/apb_api/test_db.py:22: DeprecationWarning: Call to deprecated function get_server_info. Reason:
    The property counterpart 'server_info' should be used instead.

  db_info = conn.get_server_info()
Connected to MySQL Server version: 8.0.44-0ubuntu0.24.04.1
You're connected to database: apb_msp

test curl: 
(venv) apis@apissrv:~/apb_api$ curl http://localhost:8000/ping
{
  "status": "alive"
}

test number to word: 
(venv) apis@apissrv:~/apb_api$ curl -X POST http://localhost:8000/number-to-words \
>          -H "Authorization: Bearer 8c57a7c3dfe7307abf40c9e35d0508ba6d2e2c4dda27ae66567627b0da5d68ae" \
>          -H "Content-Type: application/json" \
>          -d '{"number": "500.25"}'
{
  "code": "200",
  "data": {
    "number": "500.25",
    "words": "\u0eab\u0ec9\u0eb2\u0eae\u0ec9\u0ead\u0e8d\u0e88\u0eb8\u0e94\u0eaa\u0ead\u0e87\u0eab\u0ec9\u0eb2"
  },
  "message": "success"
}

test new keycode: 
(venv) apis@apissrv:~/apb_api$ curl -X POST http://localhost:8000/msp/upload \
>           -H "Authorization: Bearer 8c57a7c3dfe7307abf40c9e35d0508ba6d2e2c4dda27ae66567627b0da5d68ae" \
>           -H "Content-Type: application/json" \
>           -d '{
>                  "keyCode": "APB",
>                  "signDate": "2025-12-22",
>                  "trn_id": "12345",
>                  "sign": "8690019f3178c018d77e3b68460a58ce",
>                  "trn_desc": "Test MSP Upload for Ubuntu",
>                 "bid_date": "2025-12-22",
>                 "debit": [{"dr_ac": "1101001", "dr_amt": "500000.00"}],
>                 "credit": [{"cr_ac": "2102005", "cr_amt": "500000.00"}]
>              }'
{
  "code": "200",
  "data": {
    "trn_id": "12345"
  },
  "message": "MSP transaction uploaded successfully"
}

test from notebook:
 Run this on your Ubuntu terminal to find your IP:
 
  2. Configure Postman
  Open Postman and create a new request:

start with http, not yet setup reverse proxy
get
http://apis.com.la:8000/ping
with token


test upload 



   * Method: POST
   * URL: http://apis.com.la:8000/msp/upload
   * Auth Tab:
       * Select Type: Bearer Token
       * Token: 8c57a7c3dfe7307abf40c9e35d0508ba6d2e2c4dda27ae66567627b0da5d68ae
   * Headers Tab:
       * Ensure Content-Type is set to application/json
   * Body Tab:
       * Select raw and choose JSON from the dropdown.
       * Paste the following JSON:

    1 {
    2     "keyCode": "APB",
    3     "signDate": "2025-12-22",
    4     "trn_id": "12346",
    5     "sign": "a90df154238e93297a7a51804b494632",
    6     "trn_desc": "Postman Test from Notebook",
    7     "bid_date": "2025-12-22",
    8     "debit": [
    9         {
   10             "dr_ac": "1101001",
   11             "dr_amt": "500000.00"
   12         }
   13     ],
   14     "credit": [
   15         {
   16             "cr_ac": "2102005",
   17             "cr_amt": "500000.00"
   18         }
   19     ]
   20 }
5. create apb_msp service (see also 27 in jdb doc and put here your new one)
5. test
5. after testing check how to compile 
