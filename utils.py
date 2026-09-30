import enum
import json
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from cryptography.fernet import Fernet


def deep_serialize(obj):
    """
    Recursively converts Decimals, UUIDs, Enums, and datetimes 
    into JSON-safe structures for API responses.
    """
    if obj is None:
        return None
    if isinstance(obj, (int, float, bool, str)):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): deep_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [deep_serialize(item) for item in obj]
    
    # Fallback for other objects
    return str(obj)


def calculate_duration(start, end):
    """
    Calculates ISO datetime difference in seconds for job duration reporting.
    """
    if isinstance(start, str):
        start = datetime.fromisoformat(start)
    if isinstance(end, str):
        end = datetime.fromisoformat(end)
        
    duration = (end - start).total_seconds()
    return max(0.0, float(duration))


def build_pagination_info(page: int, page_size: int, total: int) -> dict:
    """
    Generates standard pagination envelope.
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


class Encrypter:
    """
    Fernet-based symmetric encryption utility for sensitive data at rest.
    """
    def __init__(self, key: bytes = None):
        if key is None:
            key = Fernet.generate_key()
        self.cipher = Fernet(key)

    def encrypt(self, data: str) -> str:
        if not data:
            return ""
        return self.cipher.encrypt(data.encode('utf-8')).decode('utf-8')

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        return self.cipher.decrypt(token.encode('utf-8')).decode('utf-8')