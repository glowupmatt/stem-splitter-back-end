def get_audio_info(input_path):
    """Get audio sample rate using ffprobe"""
    import subprocess
    import json
    
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        input_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    
    for stream in data['streams']:
        if stream['codec_type'] == 'audio':
            return int(stream['sample_rate'])
    
    return 44100  # fallback to CD quality if detection fails