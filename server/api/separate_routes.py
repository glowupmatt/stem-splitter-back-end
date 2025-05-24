import sys
import os
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


def ensure_ffmpeg():
    """Ensure FFmpeg is installed and available."""
    if not check_ffmpeg():
        try:
            print("FFmpeg not found. Installing...")
            install_ffmpeg()
            print("FFmpeg installed successfully.")
            return True
        except Exception as e:
            return jsonify({"error": f"Failed to install FFmpeg: {str(e)}"}), 500
    else:
        print("FFmpeg is already installed.")
        return True

def prepare_audio_file(url):
    """Download and prepare the audio file for processing."""
    if not url:
        return None, None, (jsonify({"error": "No audio URL provided"}), 400)
    
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
        
        return temp_path, safe_filename, None
    except Exception as e:
        return None, None, (jsonify({
            "error": f"Failed to prepare audio file: {str(e)}",
            "details": str(e)
        }), 500)
        
def run_separation(temp_path, mode="2"):
    """Run the audio separation using demucs."""

    separation_start = perf_counter()
    output_dir = Path("separated/htdemucs") / temp_path.stem
    
    try:
        cmd_args = ["--mp3"]
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
        
        separation_time = perf_counter() - separation_start
        return stems_files, output_dir, separation_time, None
    except Exception as e:
        return None, output_dir, 0, jsonify({"error": f"Separation failed: {str(e)}"}), 500
    
def upload_stems_to_s3(stems_files, safe_filename):
    """Upload the separated stems to S3 and generate download links."""
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    s3_client = boto3.client('s3')
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
            return None, jsonify({"error": f"Error processing {stem}: {str(e)}"}), 500
        
    return download_links, None

def clean_up_files(temp_path, output_dir):
    """Clean up temporary files and directories."""
    if temp_path and temp_path.exists():
        temp_path.unlink()
    if output_dir and output_dir.exists():
        shutil.rmtree(output_dir)
            
            

@separate_routes.route("/", methods=['POST'])
def separate_audio():
    """Main route handler for audio separation."""
    start_time = perf_counter()
    
    ffmpeg_result = ensure_ffmpeg()
    if not isinstance(ffmpeg_result, bool):
        return ffmpeg_result
    
    url = request.form.get('link')
    temp_path, safe_filename, error = prepare_audio_file(url)
    if error:
        return error
    
    try:
        mode = request.form.get('mode', '2')
        separation_result = run_separation(temp_path, mode)
        
        if len(separation_result) == 5:  # Error case
            stems_files, output_dir, separation_time, error = separation_result
            clean_up_files(temp_path, output_dir)
            return error
        
        stems_files, output_dir, separation_time, _ = separation_result
        
        upload_result = upload_stems_to_s3(stems_files, safe_filename)
        if len(upload_result) == 3:  # Error case
            clean_up_files(temp_path, output_dir)
            return upload_result[1]
        
        download_links, _ = upload_result
        
        clean_up_files(temp_path, output_dir)
        
        return jsonify({
            "message": "Separation complete",
            "downloads": download_links,
            "processing_time": perf_counter() - start_time,
            "separation_time": separation_time,
        })

    except Exception as e:
        clean_up_files(temp_path, output_dir if 'output_dir' in locals() else None)
        return jsonify({
            "error": f"Separation failed: {str(e)}",
            "details": str(e)
        }), 500