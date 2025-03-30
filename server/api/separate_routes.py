import sys
import os
import tempfile
import shutil
from pathlib import Path
from time import perf_counter
import boto3
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import demucs.separate
from dotenv import load_dotenv
from utils.install_ffmpeg import install_ffmpeg, check_ffmpeg
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()
separate_routes = Blueprint("audio", __name__)

ALLOWED_EXTENSIONS = {'wav', 'mp3'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@separate_routes.route("/", methods=['POST'])
def separate_audio():
    if not check_ffmpeg():
        try:
            print("FFmpeg not found. Installing...")
            install_ffmpeg()
            print("FFmpeg installed successfully.")
        except Exception as e:
            return jsonify({"error": f"Failed to install FFmpeg: {str(e)}"}), 500
    else:
        print("FFmpeg is already installed.")
    
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
        # Create a secure filename
        safe_filename = secure_filename(file.filename)
        
        # Create temp directory if it doesn't exist
        temp_dir = Path('temp')
        temp_dir.mkdir(exist_ok=True)
        
        # Create temporary file with proper extension in our temp directory
        temp_path = temp_dir / safe_filename
        file.save(str(temp_path))

        # Upload original to S3
        s3_client = boto3.client('s3')
        s3_path = f"originals/{safe_filename}"
        
        with open(temp_path, 'rb') as file_data:
            s3_client.upload_fileobj(
                file_data,
                bucket_name,
                s3_path,
                ExtraArgs={
                    'ContentType': 'audio/mpeg',
                    'ACL': 'public-read'
                }
            )

        # Generate URL for original file
        original_url = f"https://{bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_path}"

        # Process stems
        stems_files = {}
        output_dir = Path('separated/htdemucs') / Path(safe_filename).stem
        separation_start = perf_counter()

        # Separate audio into stems
        try:
            mode = request.form.get('mode', '2')
            
            # Build the command arguments
            cmd_args = ["--mp3"]
            if mode == '2':
                cmd_args.extend(["--two-stems", "vocals"])
            cmd_args.extend(["-n", "htdemucs", str(temp_path)])
            
            # Run the separation
            demucs.separate.main(cmd_args)

            # Get the output directory path
            output_dir = Path("separated/htdemucs") / temp_path.stem
            
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

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            return jsonify({"error": f"Separation failed: {str(e)}"}), 500

        separation_time = perf_counter() - separation_start
        
        # Upload stems to S3
        download_links = {}
        for stem, stem_path in stems_files.items():
            try:
                stem_filename = f"{stem}_{safe_filename}"
                s3_stem_path = f"stems/{stem_filename}"
                
                with open(stem_path, 'rb') as stem_data:
                    s3_client.upload_fileobj(
                        stem_data,
                        bucket_name,
                        s3_stem_path,
                        ExtraArgs={
                            'ContentType': 'audio/mpeg',
                            'ACL': 'public-read'
                        }
                    )
                
                download_links[stem] = f"https://{bucket_name}.s3.{os.getenv('AWS_DEFAULT_REGION')}.amazonaws.com/{s3_stem_path}"
                os.unlink(stem_path)
                
            except Exception as e:
                return jsonify({"error": f"Error processing {stem}: {str(e)}"}), 500

        # Clean up
        if temp_path.exists():
            temp_path.unlink()
        if output_dir.exists():
            shutil.rmtree(output_dir)

        return jsonify({
            "message": "Separation complete",
            "downloads": download_links,
            "processing_time": perf_counter() - start_time,
            "separation_time": separation_time,
            "original_file": original_url
        })

    except Exception as e:
        # Clean up on error
        if 'temp_path' in locals() and temp_path.exists():
            temp_path.unlink()
        if 'output_dir' in locals() and output_dir.exists():
            shutil.rmtree(output_dir)
        return jsonify({
            "error": f"Separation failed: {str(e)}",
            "details": str(e)
        }), 500