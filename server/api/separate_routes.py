import sys
import os
import io
import time
from dotenv import load_dotenv
from pathlib import Path
import tempfile
import boto3
from flask import Blueprint, request, jsonify
sys.path.append(str(Path(__file__).parent.parent))
import demucs.separate
from werkzeug.utils import secure_filename
from time import perf_counter
import uuid

load_dotenv()
separate_routes = Blueprint("audio", __name__)

ALLOWED_EXTENSIONS = {'wav', 'mp3'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@separate_routes.route("/", methods=['POST'])
def separate_audio():
    start_time = perf_counter()
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    try:
        # Read file content into memory
        file_content = file.read()

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name

        # Generate a safe unique filename
        safe_filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"

        # Upload original file to S3
        s3_path = f"originals/{safe_filename}"
        s3_client = boto3.client('s3')
        
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

        # Generate URL for original file
        original_url = f"https://{bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_path}"

        # Separate audio into stems
        try:
            separation_start = perf_counter()
            mode = request.form.get('mode', '2')
            
            # Build the command arguments
            cmd_args = ["--mp3"]
            if mode == '2':
                cmd_args.extend(["--two-stems", "vocals"])
            cmd_args.extend(["-n", "htdemucs", temp_path])
            
            # Run the separation
            demucs.separate.main(cmd_args)
            separation_time = perf_counter() - separation_start

            # Get the output directory path
            output_dir = Path("separated/htdemucs") / Path(temp_path).stem
            
            # Define stems based on mode
            if mode == '2':
                stems_files = {
                    'vocals': str(output_dir / "vocals.mp3"),
                    'instrumental': str(output_dir / "no_vocals.mp3")
                }
            else:
                stems_files = {
                    'vocals': str(output_dir / "vocals.mp3"),
                    'drums': str(output_dir / "drums.mp3"),
                    'bass': str(output_dir / "bass.mp3"),
                    'other': str(output_dir / "other.mp3")
                }
            
            # Clean up temporary input file
            os.unlink(temp_path)

        except Exception as e:
            return jsonify({"error": f"Separation failed: {str(e)}"}), 500

        # Upload stems to S3
        download_links = {}
        for stem, stem_path in stems_files.items():
            try:
                # Upload the file to S3
                stem_filename = f"{stem}_{safe_filename}"
                s3_path = f"stems/{stem_filename}"
                retry_count = 0
                max_retries = 5
                
                # Retry logic for uploading to S3
                while retry_count < max_retries:
                    try:
                        with open(stem_path, 'rb') as file_data:
                            s3_client.upload_fileobj(
                                file_data,
                                bucket_name,
                                s3_path,
                                ExtraArgs={
                                    'ContentType': 'audio/mpeg',
                                    'ACL': 'public-read'
                                }
                            )
                        break
                    except PermissionError:
                        retry_count += 1
                        if retry_count == max_retries:
                            return jsonify({"error": f"Could not upload {stem} to S3"}), 500
                        time.sleep(1)
                
                # Generate download link
                download_links[stem] = f"https://{bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_path}"
                
                # Clean up stem file
                os.unlink(stem_path)
                
            except Exception as e:
                return jsonify({"error": f"Error processing {stem}: {str(e)}"}), 500

        # Clean up the separated directory
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)

        return jsonify({
            "message": "Separation complete",
            "downloads": download_links,
            "processing_time": perf_counter() - start_time,
            "separation_time": separation_time,
            "original_file": original_url
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Separation failed: {str(e)}",
            "details": str(e)
        }), 500