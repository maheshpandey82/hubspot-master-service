import hashlib
import hmac
import time
import requests

url = "http://127.0.0.1:8000/api/scan/start"
secret = "super-secret-coordinator-key"
ts = str(int(time.time()))
body = b'{"organization_id":"org_demo_123","object_types":["contacts","companies"]}'

# Compute SHA256 Hash of body
h = hashlib.sha256(body).hexdigest()

# Create Canonical String
canon = f"POST\n/api/scan/start\n{ts}\nnonce_demo_123\n{h}"

# Compute HMAC Signature
sig = hmac.new(secret.encode(), canon.encode(), hashlib.sha256).hexdigest()

headers = {
    "X-HS-Signature": sig,
    "X-HS-Timestamp": ts,
    "X-HS-Client-ID": "coordinator_client",
    "X-HS-Nonce": "nonce_demo_123",
    "Content-Type": "application/json",
}

print("Sending Scan Request...")
response = requests.post(url, data=body, headers=headers)
print("Response Status Code:", response.status_code)
print("Response Output:", response.json())