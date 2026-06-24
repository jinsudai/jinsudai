"""S3 tasks for uploading files to AWS S3."""

import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def upload_file_to_s3(
    file_path: str,
    bucket_name: str,
    s3_key: str,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region: str = "us-east-1",
    endpoint_url: Optional[str] = None
) -> dict:
    """
    Upload a file to S3.

    Args:
        file_path: Local path to the file to upload
        bucket_name: S3 bucket name
        s3_key: S3 key (path within the bucket)
        aws_access_key_id: AWS access key ID (optional, uses env vars if not provided)
        aws_secret_access_key: AWS secret access key (optional, uses env vars if not provided)
        aws_region: AWS region (default: us-east-1)
        endpoint_url: Custom endpoint URL (for S3-compatible services like MinIO)

    Returns:
        dict: Contains status, s3_uri, and metadata
    """
    try:
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
            endpoint_url=endpoint_url
        )

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Upload file
        logger.info(f"Uploading {file_path} to s3://{bucket_name}/{s3_key}")
        s3_client.upload_file(str(file_path_obj), bucket_name, s3_key)

        # Get file metadata
        file_size = file_path_obj.stat().st_size

        s3_uri = f"s3://{bucket_name}/{s3_key}"

        logger.info(f"✅ Successfully uploaded to {s3_uri}")

        return {
            "status": "success",
            "s3_uri": s3_uri,
            "bucket": bucket_name,
            "key": s3_key,
            "file_size": file_size,
            "file_name": file_path_obj.name
        }

    except NoCredentialsError:
        logger.error("AWS credentials not found")
        return {
            "status": "error",
            "error": "AWS credentials not found"
        }
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error during S3 upload: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
