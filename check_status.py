import sys
import hashlib
import hmac
import time
import requests

# Terminal command line argument se scan_id lene ke liye
if len(sys.argv) > 1:
    scan_id = sys.argv[1]
else:
    print("Error: Please provide a scan_id!")
    print("Example: python check_status.py <scan_id>")
    sys.exit(1)

path = f"/api/scan/{scan_id}/status"
url = f"http://127.0.0.1:8000{path}"

secret = "super-secret-coordinator-key"
ts = str(int(time.time()))
body = b""

h = hashlib.sha256(body).hexdigest()
canon = f"GET\n{path}\n{ts}\nnonce_status_{int(time.time())}\n{h}"
sig = hmac.new(secret.encode(), canon.encode(), hashlib.sha256).hexdigest()

headers = {
    "X-HS-Signature": sig,
    "X-HS-Timestamp": ts,
    "X-HS-Client-ID": "coordinator_client",
    "X-HS-Nonce": f"nonce_status_{int(time.time())}",
}

response = requests.get(url, headers=headers)
print("\nStatus Output:", response.json())