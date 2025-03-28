import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def upload_to_s3(file_path, s3_path, bucket_name, content_type='audio/mpeg'):
    """
    Upload a file to S3
    Args:
        file_path (Path): Local path to file
        s3_path (str): Path in S3 bucket (e.g., 'stems/file.mp3')
        bucket_name (str): Name of S3 bucket
        content_type (str): MIME type of file
    Returns:
        str: S3 URL of uploaded file
    """
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION')
        )
        
        with open(file_path, 'rb') as file_data:
            s3_client.upload_fileobj(
                file_data,
                bucket_name,
                s3_path,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'public-read'
                }
            )
        
        # Return the S3 URL
        return f"https://{bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_path}"
    
    except Exception as e:
        return(f"Error uploading to S3: {str(e)}")