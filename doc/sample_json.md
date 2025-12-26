Upload;

Example: LAK

postman request POST 'http://apis.com.la:8000/msp/upload' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer 8c57a7c3dfe7307abf40c9e35d0508ba6d2e2c4dda27ae66567627b0da5d68ae' \
  --body '{
    "trn_id": "11403",
    "trn_desc": "Daily total",
    "currency": "LAK",
    "acc_book": "wallet",
    "bis_date": "2025-12-22",
    "status": "wait",
    "create_date": "2025-12-23 00:10:00",

    "debit": [
        {
            "dr_ac": "6281.02",
            "dr_amt": "100000000",
            "dr_desc": "fee 1"
        },
        {
            "dr_ac": "6111.1",
            "dr_amt": "2000000",
            "dr_desc": "fee 2"
        }
    ],

    "credit": [
        {
            "cr_ac": "1201.23",
            "cr_amt": "102000000"
        }
    ]
}
' \
  --auth-bearer-token '8c57a7c3dfe7307abf40c9e35d0508ba6d2e2c4dda27ae66567627b0da5d68ae'

 Example: USD;

  postman request POST 'http://apis.com.la:8000/msp/upload' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer 8c57a7c3dfe7307abf40c9e35d0508ba6d2e2c4dda27ae66567627b0da5d68ae' \
  --body '{
    "trn_id": "11404",
    "trn_desc": "Daily total",
    "currency": "USD",
    "ex_rate": 21000,
    "acc_book": "wallet",
    "bis_date": "2025-12-22",
    "status": "wait",
    "create_date": "2025-12-23 00:10:00",

    "debit": [
        {
            "dr_ac": "6281.02",
            "dr_amt": "100000000",
            "dr_amt_lak": "1000000000",
            "dr_desc": "fee 1"
        },
        {
            "dr_ac": "6111.1",
            "dr_amt": "2000000",
            "dr_amt_lak": "20000000",
            "dr_desc": "fee 2"
        }
    ],

    "credit": [
        {
            "cr_ac": "1201.23",
            "cr_amt": "102000000",
            "cr_amt_lak": "1020000000"
        }
    ]
}
' \
  --auth-bearer-token '8c57a7c3dfe7307abf40c9e35d0508ba6d2e2c4dda27ae66567627b0da5d68ae'