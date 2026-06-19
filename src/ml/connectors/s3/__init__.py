"""S3 connector for uploading files to AWS S3."""

from ml.connectors.s3.s3_tasks import upload_file_to_s3_task

__all__ = ['upload_file_to_s3_task']
