import unittest
from unittest.mock import patch, mock_open, MagicMock
import sys
from pathlib import Path
from flask import Flask
import os

sys.path.append(str(Path(__file__).parent.parent))
from server.api.separate_routes import upload_stems_to_s3


class TestUploadStemsToS3(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        self.safe_filename = "test_song.mp3"
        self.stems_files = {
            'vocals': '/tmp/vocals.mp3',
            'drums': '/tmp/drums.mp3',
            'bass': '/tmp/bass.mp3',
            'other': '/tmp/other.mp3'
        }
        
        os.environ['AWS_BUCKET_NAME'] = 'test-bucket'
        os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'

    def tearDown(self):
        self.app_context.pop()

    @patch('boto3.client')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test audio data')
    @patch('os.unlink')
    def test_upload_stems_to_s3_success(self, mock_unlink, mock_file_open, mock_boto3_client):
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        result, error = upload_stems_to_s3(self.stems_files, self.safe_filename)
        
        self.assertIsNone(error)
        self.assertEqual(len(result), 4)
        
        for stem in self.stems_files:
            expected_url = f"https://test-bucket.s3.us-west-2.amazonaws.com/stems/{stem}_{self.safe_filename}"
            self.assertEqual(result[stem], expected_url)
            
            mock_s3.upload_fileobj.assert_any_call(
                mock_file_open.return_value,
                'test-bucket',
                f"stems/{stem}_{self.safe_filename}",
                ExtraArgs={
                    'ContentType': 'audio/mpeg',
                    'ACL': 'public-read'
                }
            )
            
            mock_unlink.assert_any_call(self.stems_files[stem])
        
        self.assertEqual(mock_s3.upload_fileobj.call_count, 4)
        self.assertEqual(mock_unlink.call_count, 4)
        self.assertEqual(mock_file_open.call_count, 4)

    @patch('boto3.client')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.unlink')
    def test_upload_stems_to_s3_exception(self, mock_unlink, mock_file_open, mock_boto3_client):
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.upload_fileobj.side_effect = Exception("Upload failed")
        
        result = upload_stems_to_s3(self.stems_files, self.safe_filename)
        
        self.assertEqual(len(result), 3)
        _, error_response, status_code = result
        self.assertEqual(status_code, 500)
        self.assertIn("Upload failed", error_response.json["error"])
        
        mock_file_open.assert_called_once()
        mock_unlink.assert_not_called()

    @patch('boto3.client')
    @patch('builtins.open')
    @patch('os.unlink')
    def test_upload_stems_to_s3_file_open_error(self, mock_unlink, mock_open_func, mock_boto3_client):
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_open_func.side_effect = FileNotFoundError("File not found")
        
        result = upload_stems_to_s3(self.stems_files, self.safe_filename)
        
        self.assertEqual(len(result), 3)
        _, error_response, status_code = result
        self.assertEqual(status_code, 500)
        self.assertIn("File not found", error_response.json["error"])
        
        mock_s3.upload_fileobj.assert_not_called()
        mock_unlink.assert_not_called()

    @patch('boto3.client')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test audio data')
    @patch('os.unlink')
    def test_upload_stems_to_s3_delete_error(self, mock_unlink, mock_file_open, mock_boto3_client):
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        mock_unlink.side_effect = [None, PermissionError("Permission denied")]
        
        limited_stems = {
            'vocals': '/tmp/vocals.mp3',
            'drums': '/tmp/drums.mp3'
        }
        
        result = upload_stems_to_s3(limited_stems, self.safe_filename)
        
        self.assertEqual(len(result), 3) 
        _, error_response, status_code = result
        self.assertEqual(status_code, 500)
        self.assertIn("Permission denied", error_response.json["error"])
        
        self.assertEqual(mock_s3.upload_fileobj.call_count, 2)
        self.assertEqual(mock_unlink.call_count, 2)


if __name__ == '__main__':
    unittest.main()