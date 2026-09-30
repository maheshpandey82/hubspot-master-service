import os
import logging
from io import BytesIO
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

class MinIOStorageClient:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.secure = os.getenv("MINIO_SECURE", "False").lower() in ("true", "1", "t")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "hubspot-data")

        # Initialize MinIO Client
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Checks if the bucket exists, creates it if not."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
            else:
                logger.info(f"MinIO bucket '{self.bucket_name}' already exists.")
        except S3Error as err:
            logger.error(f"Error checking/creating MinIO bucket: {err}")
            raise

    def upload_data(self, object_name: str, data_bytes: bytes, content_type: str = "application/json"):
        """
        Uploads in-memory bytes data to MinIO.
        :param object_name: Destination path/filename inside bucket (e.g., 'contacts/2026-09-30.json')
        :param data_bytes: Byte stream of the file content
        :param content_type: MIME type of the file
        """
        try:
            data_stream = BytesIO(data_bytes)
            stream_length = len(data_bytes)

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                length=stream_length,
                content_type=content_type
            )
            logger.info(f"Successfully uploaded '{object_name}' to bucket '{self.bucket_name}'.")
            return f"{self.bucket_name}/{object_name}"
        except S3Error as err:
            logger.error(f"Failed to upload '{object_name}' to MinIO: {err}")
            raise

    def upload_file(self, file_path: str, object_name: str = None):
        """
        Uploads a local file from disk to MinIO.
        """
        if not object_name:
            object_name = os.path.basename(file_path)

        try:
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path
            )
            logger.info(f"Successfully uploaded file '{file_path}' as '{object_name}'.")
            return f"{self.bucket_name}/{object_name}"
        except S3Error as err:
            logger.error(f"Failed to upload local file '{file_path}': {err}")
            raise