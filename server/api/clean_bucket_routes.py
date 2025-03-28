import os
from flask import Blueprint, jsonify, request
import boto3

clean_bucket_routes = Blueprint("clean_bucket", __name__)

@clean_bucket_routes.route("/", methods=['DELETE'])
def clean_bucket_handler():
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')
        bucket_name = os.getenv('AWS_BUCKET_NAME')

        # List all objects in the bucket
        paginator = s3_client.get_paginator('list_objects_v2')
        
        # Delete all objects including those in subdirectories
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                objects_to_delete = [{'Key': obj['Key']} for obj in page['Contents']]
                if objects_to_delete:
                    s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': objects_to_delete}
                    )
                    print(f"Deleted {len(objects_to_delete)} objects")

        return jsonify({
            "message": "Bucket cleaned successfully",
            "bucket": bucket_name
        }), 200

    except Exception as e:
        print(f"Error cleaning bucket: {str(e)}")
        return jsonify({
            "error": f"Failed to clean bucket: {str(e)}"
        }), 500