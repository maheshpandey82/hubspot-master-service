from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from service import JobService, ExtractionService, JobStatus
from normalizer import NormalizationService
from utils import deep_serialize
from auth import hmac_auth_required
from minio_client import MinIOStorageClient
from dlq import DeadLetterQueue

app = FastAPI(title="HubSpot Master Service", version="1.0.0")


class ScanStartRequest(BaseModel):
    organization_id: str
    object_types: list[str] = Field(default=["contacts", "companies", "deals", "tickets", "owners"])


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "hubspot-master-service"}


# Secure Endpoints using HMAC Auth Dependency
@app.post("/api/scan/start", status_code=202, dependencies=[Depends(hmac_auth_required)])
def start_scan(request: ScanStartRequest):
    job = ExtractionService.start_scan(request.organization_id, request.object_types)
    return {"message": "Scan started successfully", "scan_id": job["id"], "status": job["status"]}


@app.get("/api/scan/{scan_id}/status", dependencies=[Depends(hmac_auth_required)])
def get_scan_status(scan_id: str):
    job = JobService.get_job(scan_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan ID not found")
    return deep_serialize(job)


@app.post("/api/scan/{scan_id}/pause", dependencies=[Depends(hmac_auth_required)])
def pause_scan(scan_id: str):
    job = JobService.get_job(scan_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan ID not found")
    if job["status"] not in [JobStatus.RUNNING, JobStatus.PENDING]:
        raise HTTPException(status_code=400, detail=f"Cannot pause job in state {job['status']}")
    
    JobService.update_status(scan_id, JobStatus.PAUSED)
    return {"message": "Scan pause requested", "scan_id": scan_id}


@app.post("/api/scan/{scan_id}/resume", dependencies=[Depends(hmac_auth_required)])
def resume_scan(scan_id: str):
    job = JobService.get_job(scan_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan ID not found")
    if job["status"] not in [JobStatus.PAUSED, JobStatus.CRASHED]:
        raise HTTPException(status_code=400, detail=f"Cannot resume job in state {job['status']}")
    
    JobService.update_status(scan_id, JobStatus.RESUMING)
    return {"message": "Scan resuming", "scan_id": scan_id}


@app.post("/api/scan/{scan_id}/cancel", dependencies=[Depends(hmac_auth_required)])
def cancel_scan(scan_id: str):
    job = JobService.get_job(scan_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan ID not found")
    
    JobService.update_status(scan_id, JobStatus.CANCELLED)
    return {"message": "Scan cancelled", "scan_id": scan_id}


@app.get("/api/normalization/supported-objects", dependencies=[Depends(hmac_auth_required)])
def get_supported_objects():
    return {
        "supported_objects": list(NormalizationService.NORMALIZERS.keys())
    }


@app.get("/api/dlq/records", dependencies=[Depends(hmac_auth_required)])
def get_dlq_records():
    return {"dlq_records": DeadLetterQueue.get_all_dlq_records()}