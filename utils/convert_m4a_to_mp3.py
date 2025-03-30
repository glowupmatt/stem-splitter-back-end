from utils.get_audio_info import get_audio_info

def convert_m4a_to_mp3(input_path, output_path):
    """Convert M4A file to MP3 format using ffmpeg"""
    import subprocess
        
    # Get original sample rate
    original_sample_rate = get_audio_info(input_path)
    print(f"Detected original sample rate: {original_sample_rate} Hz")
    
    try:
        # Use ffmpeg to convert M4A to MP3
        subprocess.run([
            'ffmpeg',
            '-i', input_path,  # Input file
            '-acodec', 'libmp3lame',  # Use MP3 codec
            '-ab', '320k',  # Set bitrate to 320kbps
            '-ar', str(original_sample_rate),
            '-y',  # Overwrite output file if it exists
            output_path
        ], check=True)
        return True, original_sample_rate
    except subprocess.CalledProcessError as e:
        print(f"Error converting file: {str(e)}")
        return False, None