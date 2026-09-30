import hmac
import hashlib
import time
import os
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader

# Environment key configuration
HMAC_SECRET_KEY = os.getenv("HMAC_SECRET_KEY_CORE", "super-secret-coordinator-key")
MAX_TIMESTAMP_AGE_SECONDS = 300  # 5 minutes replay protection window

header_signature = APIKeyHeader(name="X-HS-Signature", auto_error=False)
header_timestamp = APIKeyHeader(name="X-HS-Timestamp", auto_error=False)
header_client_id = APIKeyHeader(name="X-HS-Client-ID", auto_error=False)
header_nonce = APIKeyHeader(name="X-HS-Nonce", auto_error=False)


async def hmac_auth_required(request: Request):
    """
    FastAPI Dependency: Verifies HMAC-SHA256 request signatures.
    Canonical format: METHOD\nPATH\nTIMESTAMP\nNONCE\nSHA256(BODY)
    """
    signature = request.headers.get("X-HS-Signature")
    timestamp = request.headers.get("X-HS-Timestamp")
    client_id = request.headers.get("X-HS-Client-ID")
    nonce = request.headers.get("X-HS-Nonce")

    # 1. Missing header checks
    if not all([signature, timestamp, client_id, nonce]):
        raise HTTPException(
            status_code=401,
            detail="Missing required HMAC security headers (X-HS-Signature, X-HS-Timestamp, X-HS-Client-ID, X-HS-Nonce)"
        )

    # 2. Timestamp freshness check (Replay prevention)
    try:
        req_timestamp = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - req_timestamp) > MAX_TIMESTAMP_AGE_SECONDS:
            raise HTTPException(status_code=401, detail="Request timestamp expired or outside freshness window")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp format")

    # 3. Read body and build canonical string
    body = await request.body()
    body_hash = hashlib.sha256(body).hexdigest()

    canonical_string = f"{request.method.upper()}\n{request.url.path}\n{timestamp}\n{nonce}\n{body_hash}"

    # 4. Compute expected HMAC signature
    computed_signature = hmac.new(
        HMAC_SECRET_KEY.encode("utf-8"),
        canonical_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # 5. Constant time comparison to prevent timing attacks
    if not hmac.compare_digest(computed_signature, signature):
        raise HTTPException(status_code=403, detail="Invalid HMAC signature")

    return True