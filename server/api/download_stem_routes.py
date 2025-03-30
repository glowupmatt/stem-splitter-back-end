import sys
from pathlib import Path
import boto3
from urllib.parse import urlparse
from flask import Blueprint, send_file, jsonify
import io
import os
sys.path.append(str(Path(__file__).parent.parent))

download_stem_routes = Blueprint("download", __name__)

@download_stem_routes.route("/<path:file_url>")
def download_file(file_url):
    try:
        # Add debug logging
        print(f"Attempting to download: {file_url}")
        
        parsed_url = urlparse(file_url)
        bucket_name = parsed_url.netloc.split('.')[0]
        key = parsed_url.path.lstrip('/')
        
        filename = os.path.basename(key)

        s3_client = boto3.client('s3')
        try:
            s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        except Exception as aws_error:
            print(f"AWS Error: {str(aws_error)}")
            return jsonify({"error": f"AWS Authentication failed: {str(aws_error)}"}), 403
        file_obj = io.BytesIO()
        s3_client.download_fileobj(
            bucket_name,
            key,
            file_obj
        )
        
        # Seek to beginning of file
        file_obj.seek(0)
        
        return send_file(
            file_obj,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"File download failed: {str(e)}"}), 404