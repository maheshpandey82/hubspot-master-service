import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DLQ_FILE_PATH = os.getenv("DLQ_FILE_PATH", "dlq_records.json")


class DeadLetterQueue:
    @staticmethod
    def push_failed_record(scan_id: str, object_type: str, raw_record: dict, error_message: str):
        """
        Appends a failed record payload along with context to the local DLQ log file.
        """
        dlq_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "scan_id": scan_id,
            "object_type": object_type,
            "error_message": error_message,
            "raw_record": raw_record
        }

        records = []
        if os.path.exists(DLQ_FILE_PATH):
            try:
                with open(DLQ_FILE_PATH, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except json.JSONDecodeError:
                records = []

        records.append(dlq_entry)

        with open(DLQ_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        logger.error(f"[DLQ] Record for '{object_type}' in scan '{scan_id}' logged to DLQ: {error_message}")

    @staticmethod
    def get_all_dlq_records() -> list:
        """Retrieves all logged DLQ records."""
        if not os.path.exists(DLQ_FILE_PATH):
            return []
        try:
            with open(DLQ_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []