import pyodbc

# Connection details
server = '10.151.149.90'
database = 'FN_APB2025'
username = 'sa'
password = 'Apb@2k25'
driver = '{ODBC Driver 18 for SQL Server}'

# Connection string
# Note: Encrypt=yes and TrustServerCertificate=yes are required for Driver 18 
# if the server does not have a valid SSL certificate.
conn_str = (
    f"DRIVER={driver};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
    f"Connection Timeout=30;"
)

print(f"Attempting to connect to {server}...")

try:
    conn = pyodbc.connect(conn_str)
    print("-----------------------------------------")
    print("SUCCESS: Connected to MSSQL Server!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    row = cursor.fetchone()
    print(f"Server Version: {row[0]}")
    print("-----------------------------------------")
    
    conn.close()
except Exception as e:
    print("-----------------------------------------")
    print("ERROR: Could not connect to MSSQL Server.")
    print(f"Details: {str(e)}")
    print("-----------------------------------------")
