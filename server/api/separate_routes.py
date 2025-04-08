import sys
import os
import torch
import shutil
from pathlib import Path
from time import perf_counter
import boto3
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import demucs.separate
from dotenv import load_dotenv
from utils.install_ffmpeg import install_ffmpeg, check_ffmpeg
import requests
import urllib.parse 
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()
separate_routes = Blueprint("audio", __name__)

ALLOWED_EXTENSIONS = {'wav', 'mp3'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def download_file_from_url(url, download_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(download_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return download_path

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
        
        
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    start_time = perf_counter()
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    
    url = request.form.get('link')
    if not url:
        return jsonify({"error": "No audio URL provided"}), 400
    
    try:
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        if not filename or not allowed_file(filename):
            extension = '.mp3'
            if '.' in filename:
                extension = '.' + filename.rsplit('.', 1)[1].lower()
                if extension not in ['.mp3', '.wav']:
                    extension = '.mp3'
            
            filename = f"download{extension}"
        
        safe_filename = secure_filename(filename)

        temp_dir = Path('temp')
        temp_dir.mkdir(exist_ok=True)
        
        temp_path = temp_dir / safe_filename
        download_file_from_url(url, str(temp_path))
        

        s3_client = boto3.client('s3')

        stems_files = {}
        output_dir = Path('separated/htdemucs') / Path(safe_filename).stem
        separation_start = perf_counter()

        # Separate audio into stems
        try:
            mode = request.form.get('mode', '2')
            
            cmd_args = ["--mp3"]
            if device == "cuda":
                cmd_args.extend(["--device", "cuda"])
            if mode == '2':
                cmd_args.extend(["--two-stems", "vocals"])
            cmd_args.extend(["-n", "htdemucs", str(temp_path)])

            print(f"Running separation with args: {cmd_args}")
            demucs.separate.main(cmd_args)

            output_dir = Path("separated/htdemucs") / temp_path.stem
            
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
