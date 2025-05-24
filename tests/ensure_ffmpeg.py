import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from flask import Flask

sys.path.append(str(Path(__file__).parent.parent))
from server.api.separate_routes import ensure_ffmpeg


@patch('server.api.separate_routes.check_ffmpeg')
@patch('server.api.separate_routes.install_ffmpeg')
def test_ffmpeg_already_installed(mock_install_ffmpeg, mock_check_ffmpeg):

    mock_check_ffmpeg.return_value = True
    

    result = ensure_ffmpeg()
    

    assert result is True
    mock_check_ffmpeg.assert_called_once()
    mock_install_ffmpeg.assert_not_called()

@patch('server.api.separate_routes.check_ffmpeg')
@patch('server.api.separate_routes.install_ffmpeg')
def test_ffmpeg_successful_installation(mock_install_ffmpeg, mock_check_ffmpeg):
    mock_check_ffmpeg.return_value = False
    
    result = ensure_ffmpeg()
    
    assert result is True
    mock_check_ffmpeg.assert_called_once()
    mock_install_ffmpeg.assert_called_once()

@patch('server.api.separate_routes.check_ffmpeg')
@patch('server.api.separate_routes.install_ffmpeg')
def test_ffmpeg_installation_fails(mock_install_ffmpeg, mock_check_ffmpeg):
    mock_check_ffmpeg.return_value = False
    mock_install_ffmpeg.side_effect = Exception("Installation error")
    

    app = Flask(__name__)
    with app.app_context():
        result = ensure_ffmpeg()
        
        assert result[1] == 500
        assert "Failed to install FFmpeg" in result[0].json["error"]
        mock_check_ffmpeg.assert_called_once()
        mock_install_ffmpeg.assert_called_once()

if __name__ == '__main__':
    import pytest
    pytest.main([__file__])