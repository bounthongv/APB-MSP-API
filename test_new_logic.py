import requests
import json
import random
import string

# Configuration
BASE_URL = "http://localhost:5000"  # Adjust port if necessary
TOKEN = "your_test_token"  # Replace with the token from your .env or shared_utils.py default if not set
# In shared_utils.py, it looks for API_TOKEN env var. 
# If you are running locally without env, check what shared_utils expects or set it. 

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

def generate_trn_id():
    return "TEST-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def print_result(name, response, expected_status):
    status = response.status_code
    pass_fail = "PASS" if status == expected_status else "FAIL"
    print(f"[{pass_fail}] {name}")
    print(f"   Expected: {expected_status}, Got: {status}")
    if status != expected_status:
        print(f"   Response: {response.text}")
    print("-" * 30)

def test_upload():
    print("--- Starting Logic Tests ---\n")

    # 1. Valid LAK Transaction (Minimal fields)
    # Expectation: ex_rate defaults to 1, lak amounts default to original. Success (201).
    payload_lak = {
        "trn_id": generate_trn_id(),
        "trn_desc": "Test LAK Valid",
        "currency": "LAK",
        "acc_book": "123",
        "bis_date": "2025-01-01",
        "status": "wait",
        "create_date": "2025-01-01 10:00:00",
        # ex_rate omitted
        "debit": [{"dr_ac": "111", "dr_amt": "1000", "dr_desc": "test"}], # dr_amt_lak omitted
        "credit": [{"cr_ac": "222", "cr_amt": "1000", "cr_desc": "test"}] # cr_amt_lak omitted
    }
    resp = requests.post(f"{BASE_URL}/msp/upload", json=payload_lak, headers=headers)
    print_result("1. Valid LAK (Defaults)", resp, 201)

    # 2. Valid Foreign Transaction
    # Expectation: All fields provided, rate != 1, amounts differ. Success (201).
    payload_usd = {
        "trn_id": generate_trn_id(),
        "trn_desc": "Test USD Valid",
        "currency": "USD",
        "acc_book": "123",
        "bis_date": "2025-01-01",
        "status": "wait",
        "create_date": "2025-01-01 10:00:00",
        "ex_rate": "21000",
        "debit": [{"dr_ac": "111", "dr_amt": "100", "dr_amt_lak": "2100000", "dr_desc": "test"}],
        "credit": [{"cr_ac": "222", "cr_amt": "100", "cr_amt_lak": "2100000", "cr_desc": "test"}]
    }
    resp = requests.post(f"{BASE_URL}/msp/upload", json=payload_usd, headers=headers)
    print_result("2. Valid USD (Full Fields)", resp, 201)

    # 3. Invalid Foreign - Missing Rate
    # Expectation: Fail (400)
    payload_fail_1 = payload_usd.copy()
    payload_fail_1["trn_id"] = generate_trn_id()
    del payload_fail_1["ex_rate"]
    resp = requests.post(f"{BASE_URL}/msp/upload", json=payload_fail_1, headers=headers)
    print_result("3. Invalid USD (Missing Rate)", resp, 400)

    # 4. Invalid Foreign - Rate is 1
    # Expectation: Fail (400)
    payload_fail_2 = payload_usd.copy()
    payload_fail_2["trn_id"] = generate_trn_id()
    payload_fail_2["ex_rate"] = "1.00"
    resp = requests.post(f"{BASE_URL}/msp/upload", json=payload_fail_2, headers=headers)
    print_result("4. Invalid USD (Rate is 1)", resp, 400)

    # 5. Invalid Foreign - Missing LAK Amount
    # Expectation: Fail (400)
    payload_fail_3 = payload_usd.copy()
    payload_fail_3["trn_id"] = generate_trn_id()
    # Remove dr_amt_lak from first debit item
    payload_fail_3["debit"] = [{"dr_ac": "111", "dr_amt": "100", "dr_desc": "test"}] 
    resp = requests.post(f"{BASE_URL}/msp/upload", json=payload_fail_3, headers=headers)
    print_result("5. Invalid USD (Missing LAK Amount)", resp, 400)

    # 6. Invalid Foreign - LAK Amount equals Original
    # Expectation: Fail (400)
    payload_fail_4 = payload_usd.copy()
    payload_fail_4["trn_id"] = generate_trn_id()
    payload_fail_4["debit"] = [{"dr_ac": "111", "dr_amt": "100", "dr_amt_lak": "100", "dr_desc": "test"}]
    resp = requests.post(f"{BASE_URL}/msp/upload", json=payload_fail_4, headers=headers)
    print_result("6. Invalid USD (LAK Amt == Original)", resp, 400)

if __name__ == "__main__":
    test_upload()
