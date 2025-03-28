import sys
from pathlib import Path
from flask import Blueprint, send_file, jsonify
sys.path.append(str(Path(__file__).parent.parent))




download_stem_routes = Blueprint("download", __name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'outputs'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@download_stem_routes.route("/<filename>")
def download_file(filename):
    try:
        return send_file(
            OUTPUT_DIR / filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"File not found: {str(e)}"}), 404