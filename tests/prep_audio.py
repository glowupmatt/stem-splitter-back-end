import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from flask import Flask, jsonify


sys.path.append(str(Path(__file__).parent.parent))
from server.api.separate_routes import prepare_audio_file

app = Flask(__name__)

class TestPrepAudio(unittest.TestCase):
  
  @patch('server.api.separate_routes.download_file_from_url')
  @patch('server.api.separate_routes.secure_filename')
  def test_prepare_audio_file_download_exception(self, mock_secure_filename, mock_download):
    """Test handling an exception during file download."""

    url = "https://example.com/music.mp3"
    mock_secure_filename.return_value = "music.mp3"
    mock_download.side_effect = Exception("Download failed")
    

    with app.test_client() as client:
      with app.app_context():

        result = prepare_audio_file(url)
        

        self.assertEqual(len(result), 3)
        

        temp_path, filename, response = result
        

        self.assertIsNone(temp_path)
        self.assertIsNone(filename)
        

        self.assertIsInstance(response, tuple)
        self.assertEqual(response[1], 500)
        

        response_json = response[0].json
        self.assertIn("Failed to prepare audio file", response_json["error"])
        self.assertIn("Download failed", response_json["details"])
  
  @patch('server.api.separate_routes.download_file_from_url')
  @patch('server.api.separate_routes.secure_filename')
  def test_prepare_audio_file_no_url(self, mock_secure_filename, mock_download):
    """Test behavior when no URL is provided."""
    with app.app_context():

      result = prepare_audio_file(None)
      

      self.assertEqual(len(result), 3)
      

      temp_path, filename, response = result
      

      self.assertIsNone(temp_path)
      self.assertIsNone(filename)
      self.assertEqual(response[1], 400)
      self.assertIn("No audio URL provided", response[0].json["error"])
      

      mock_download.assert_not_called()
      mock_secure_filename.assert_not_called()
  
  @patch('pathlib.Path.mkdir')
  def test_prepare_audio_file_mkdir_exception(self, mock_mkdir):
    """Test handling an exception during directory creation."""

    url = "https://example.com/music.mp3"
    mock_mkdir.side_effect = PermissionError("Permission denied")
    
    with app.app_context():

      result = prepare_audio_file(url)
      

      self.assertEqual(len(result), 3)
      

      temp_path, filename, response = result
      

      self.assertIsNone(temp_path)
      self.assertIsNone(filename)
      self.assertEqual(response[1], 500)
      self.assertIn("Failed to prepare audio file", response[0].json["error"])

if __name__ == '__main__':
  unittest.main()