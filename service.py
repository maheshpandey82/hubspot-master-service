import uuid
import threading
import time
from datetime import datetime
from normalizer import NormalizationService
from utils import deep_serialize, calculate_duration


class JobStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RESUMING = "RESUMING"
    NORMALIZING = "NORMALIZING"
    UPLOADING_TO_MINIO = "UPLOADING_TO_MINIO"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    CRASHED = "CRASHED"


# In-memory storage for jobs and checkpoints
JOBS_DB = {}
CHECKPOINTS_DB = {}


class JobService:
    @staticmethod
    def create_job(organization_id: str, object_types: list[str]) -> dict:
        scan_id = str(uuid.uuid4())
        job = {
            "id": scan_id,
            "organization_id": organization_id,
            "status": JobStatus.PENDING,
            "object_types": object_types,
            "entity_record_counts": {obj: 0 for obj in object_types},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "last_heartbeat": datetime.utcnow().isoformat(),
            "error_detail": None
        }
        JOBS_DB[scan_id] = job
        CHECKPOINTS_DB[scan_id] = {obj: None for obj in object_types}
        return job

    @staticmethod
    def get_job(scan_id: str) -> dict:
        return JOBS_DB.get(scan_id)

    @staticmethod
    def update_status(scan_id: str, status: str, error_detail: str = None):
        job = JOBS_DB.get(scan_id)
        if job:
            job["status"] = status
            job["updated_at"] = datetime.utcnow().isoformat()
            if error_detail:
                job["error_detail"] = error_detail

    @staticmethod
    def update_heartbeat(scan_id: str):
        job = JOBS_DB.get(scan_id)
        if job:
            job["last_heartbeat"] = datetime.utcnow().isoformat()

    @staticmethod
    def save_checkpoint(scan_id: str, object_type: str, cursor: str, records_processed: int):
        if scan_id in CHECKPOINTS_DB:
            CHECKPOINTS_DB[scan_id][object_type] = cursor
        job = JOBS_DB.get(scan_id)
        if job:
            job["entity_record_counts"][object_type] = records_processed


class ExtractionService:
    @staticmethod
    def _run_extraction(scan_id: str):
        job = JobService.get_job(scan_id)
        if not job:
            return

        JobService.update_status(scan_id, JobStatus.RUNNING)

        try:
            for obj in job["object_types"]:
                current_job = JobService.get_job(scan_id)
                if current_job["status"] in [JobStatus.PAUSED, JobStatus.CANCELLED]:
                    return

                for page in range(1, 4):
                    time.sleep(0.2)
                    JobService.update_heartbeat(scan_id)
                    cursor = f"cursor_page_{page}"
                    records_count = page * 20
                    JobService.save_checkpoint(scan_id, obj, cursor, records_count)

            JobService.update_status(scan_id, JobStatus.NORMALIZING)
            time.sleep(0.5)
            JobService.update_status(scan_id, JobStatus.COMPLETED)

        except Exception as e:
            JobService.update_status(scan_id, JobStatus.FAILED, error_detail=str(e))

    @classmethod
    def start_scan(cls, organization_id: str, object_types: list[str]) -> dict:
        job = JobService.create_job(organization_id, object_types)
        thread = threading.Thread(target=cls._run_extraction, args=(job["id"],), daemon=True)
        thread.start()
        return job