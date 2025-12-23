import hashlib

def string_sort(value):
    """Sort the characters in a string."""
    return ''.join(sorted(value))

def generate_signature(key_code, sign_date, trn_id):
    """Generate a signature using keyCode, signDate, and trn_id."""
    concatenated = f"{key_code}{sign_date}{trn_id}"
    sorted_string = string_sort(concatenated)
    signature = hashlib.md5(sorted_string.encode()).hexdigest()
    return signature

# Input values
key_code = "APB"
sign_date = "2025-12-22"
trn_id = "12345"

# Generate the signature
signature = generate_signature(key_code, sign_date, trn_id)
print("Generated Signature:", signature)
