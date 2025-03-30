from dotenv import load_dotenv

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Third-party imports
from flask import Flask
# from flask_cors import CORS

# Local imports
from server.api.separate_routes import separate_routes
from server.api.download_stem_routes import download_stem_routes
from server.api.clean_bucket_routes import clean_bucket_routes

# Initialize Flask app
app = Flask(__name__)
app.url_map.strict_slashes = False
load_dotenv()

# CORS(app, resources={
#     r"/api/*": {
#         "origins": "*",
#         "methods": ["GET", "POST", "OPTIONS"],
#         "allow_headers": ["Content-Type", "Accept"],
#         "supports_credentials": True
#     }
# })
# Register blueprints
app.register_blueprint(separate_routes, url_prefix="/api/separate")
app.register_blueprint(download_stem_routes, url_prefix="/api/download_stem")
app.register_blueprint(clean_bucket_routes, url_prefix="/api/clean_bucket")