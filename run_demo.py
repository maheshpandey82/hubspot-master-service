import hashlib
import hmac
import time
import requests

BASE_URL = "http://127.0.0.1:8000"
SECRET = "super-secret-coordinator-key"
CLIENT_ID = "coordinator_client"

def get_headers(method: str, path: str, body: bytes = b""):
    ts = str(int(time.time()))
    nonce = f"nonce_{int(time.time()*1000)}"
    body_hash = hashlib.sha256(body).hexdigest()
    canon = f"{method}\n{path}\n{ts}\n{nonce}\n{body_hash}"
    sig = hmac.new(SECRET.encode(), canon.encode(), hashlib.sha256).hexdigest()
    return {
        "X-HS-Signature": sig,
        "X-HS-Timestamp": ts,
        "X-HS-Client-ID": CLIENT_ID,
        "X-HS-Nonce": nonce,
        "Content-Type": "application/json",
    }

# 1. Start Scan
start_path = "/api/scan/start"
start_body = b'{"organization_id":"org_demo_123","object_types":["contacts"]}'
res = requests.post(f"{BASE_URL}{start_path}", data=start_body, headers=get_headers("POST", start_path, start_body))
scan_id = res.json().get("scan_id")
print(f"Scan Started! ID: {scan_id}")

# 2. Poll Status every 2 seconds
status_path = f"/api/scan/{scan_id}/status"
for i in range(3):
    time.sleep(2)
    res_status = requests.get(f"{BASE_URL}{status_path}", headers=get_headers("GET", status_path))
    print(f"Poll {i+1} Status Output:", res_status.json())