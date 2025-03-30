import boto3
import os
from dotenv import load_dotenv
import io
import uuid

load_dotenv()

def upload_to_s3(file_content, filename, bucket_name=None):
    """Upload a file to S3 and return the public URL"""
    if bucket_name is None:
        bucket_name = os.getenv('AWS_BUCKET_NAME')
    
    s3_client = boto3.client('s3')
    safe_filename = f"{uuid.uuid4().hex}_{filename}"
    s3_path = f"stems/{safe_filename}"
    
    # Upload to S3
    s3_upload_buffer = io.BytesIO(file_content)
    s3_client.upload_fileobj(
        s3_upload_buffer,
        bucket_name,
        s3_path,
        ExtraArgs={
            'ContentType': 'audio/mpeg',
            'ACL': 'public-read'
        }
    )
    
    # Return the public URL
    return f"https://{bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_path}"