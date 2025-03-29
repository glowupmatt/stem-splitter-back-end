import os
import sys
import subprocess
import torch
import json
import torchaudio
import io
import numpy as numpy
import soundfile as sf
from demucs.pretrained import get_model
from demucs.apply import apply_model


SAMPLE_RATE = 44100
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def install_ffmpeg():
    print("Starting Ffmpeg installation...")

    subprocess.check_call([sys.executable, "-m", "pip",
                          "install", "--upgrade", "pip"])

    subprocess.check_call([sys.executable, "-m", "pip",
                          "install", "--upgrade", "setuptools"])

    try:
        subprocess.check_call([sys.executable, "-m", "pip",
                               "install", "ffmpeg-python"])
        print("Installed ffmpeg-python successfully")
    except subprocess.CalledProcessError as e:
        print("Failed to install ffmpeg-python via pip")

    try:
        subprocess.check_call([
            "wget",
            "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
            "-O", "/tmp/ffmpeg.tar.xz"
        ])

        subprocess.check_call([
            "tar", "-xf", "/tmp/ffmpeg.tar.xz", "-C", "/tmp/"
        ])

        result = subprocess.run(
            ["find", "/tmp", "-name", "ffmpeg", "-type", "f"],
            capture_output=True,
            text=True
        )
        ffmpeg_path = result.stdout.strip()

        subprocess.check_call(["cp", ffmpeg_path, "/usr/local/bin/ffmpeg"])

        subprocess.check_call(["chmod", "+x", "/usr/local/bin/ffmpeg"])

        print("Installed static FFmpeg binary successfully")
    except Exception as e:
        print(f"Failed to install static FFmpeg: {e}")

    try:
        result = subprocess.run(["ffmpeg", "-version"],
                                capture_output=True, text=True, check=True)
        print("FFmpeg version:")
        print(result.stdout)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("FFmpeg installation verification failed")
        return False


def model_fn():
    """Load pre-trained HTDemucs model
    
    Returns:
        PretrainedModel: Loaded HTDemucs model instance
    """
    model = get_model('htdemucs')
    model.eval()
    return model.to(device)

# def input_fn(request_body, request_content_type):
#     """Deserialize and preprocess audio input"""
#     if request_content_type == 'application/json':
#         input_data = json.loads(request_body)
#         audio_tensor = torch.tensor(input_data['audio'], dtype=torch.float32)
        
#     elif request_content_type in ['audio/wav', 'audio/x-wav']:
#         # Handle WAV input
#         audio_data, sr = sf.read(io.BytesIO(request_body))
#         audio_tensor = torch.tensor(audio_data, dtype=torch.float32)
#         if sr != SAMPLE_RATE:
#             resampler = torchaudio.transforms.Resample(sr, SAMPLE_RATE)
#             audio_tensor = resampler(audio_tensor)
        

#         print(f"Loaded audio with sample rate: {sr}")
        
#     elif request_content_type == 'audio/mpeg':
#         import tempfile
#         import os
        
#         # Save MP3 data to temporary file
#         with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
#             temp_file.write(request_body)
#             temp_file_path = temp_file.name
        
#         try:
#             # Use torchaudio's MP3 backend
#             audio_tensor, sr = torchaudio.load(
#                 temp_file_path,
#                 format="mp3",
#                 normalize=True  # Normalize audio to [-1, 1]
#             )
#             print(f"Loaded audio with sample rate: {sr}")
#             if sr != SAMPLE_RATE:
#                 resampler = torchaudio.transforms.Resample(sr, SAMPLE_RATE)
#                 audio_tensor = resampler(audio_tensor)
#         finally:
#             # Clean up temporary file
#             try:
#                 os.unlink(temp_file_path)
#             except:
#                 pass  # Ignore deletion errors
#     else:
#         raise ValueError(
#             f"Unsupported content type: {request_content_type}. "
#             "Supported types are: application/json, audio/wav, audio/mpeg"
#         )
    
#     # Ensure stereo audio
#     if audio_tensor.dim() == 1:
#         audio_tensor = audio_tensor.unsqueeze(0).repeat(2, 1)
#     elif audio_tensor.shape[0] == 1:
#         audio_tensor = audio_tensor.repeat(2, 1)
    
#     return audio_tensor.to(device)

def predict_fn(input_data, model):
    """Model inference for audio source separation
    
    Args:
        input_data (torch.Tensor): Input audio tensor of shape (channels, samples)
        model (PretrainedModel): Loaded HTDemucs model instance
    
    Returns:
        dict: Separated stems with keys ['drums', 'bass', 'other', 'vocals']
    """
    with torch.no_grad():
        # Add batch dimension if not present
        if input_data.dim() == 2:
            input_data = input_data.unsqueeze(0)
        
        # Run separation using Demucs apply_model
        sources = apply_model(model, input_data, split=True, device=device)
        
        # Check sources shape and structure
        if isinstance(sources, (list, tuple)):
            sources = torch.stack(sources)
            
        # Create dictionary of stems
        return {
            name: sources[0, idx]  # First batch, idx stem
            for idx, name in enumerate(model.sources)
        }

def output_fn(prediction, accept, sample_rate=44100):
    """Format prediction output
    
    Args:
        prediction (dict): Dictionary of separated stems
        accept (str): Desired output format (application/json, audio/wav, audio/mpeg)
    
    Returns:
        Union[str, bytes]: Formatted output in requested format
    """
    if accept == 'application/json':
        # Convert stems to JSON
        separated_stems = {
            name: stem.cpu().numpy().tolist()
            for name, stem in prediction.items()
        }
        return json.dumps({'separated_stems': separated_stems})
    
    elif accept in ['audio/wav', 'audio/x-wav', 'audio/mpeg']:
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            for name, stem in prediction.items():
                # Create buffer for audio file
                stem_buffer = io.BytesIO()
                
                try:
                    if accept == 'audio/mpeg':
                        # Save as MP3 without encoding_args
                        torchaudio.save(
                            stem_buffer,
                            stem.cpu(),
                            sample_rate=sample_rate,  # Use constant
                            format="mp3",
                        )
                        extension = '.mp3'
                    else:
                        # Save as WAV
                        sf.write(
                            stem_buffer,
                            stem.cpu().numpy().T,
                            samplerate=sample_rate,  # Use constant
                            format='WAV',
                        )
                        extension = '.wav'
                    # Write to zip file
                    zf.writestr(f'{name}{extension}', stem_buffer.getvalue())
                    
                finally:
                    stem_buffer.close()
                    print(f"Loaded audio with sample rate: {SAMPLE_RATE}")
        
        # Get the final bytes
        zip_bytes = buffer.getvalue()
        buffer.close()
        return zip_bytes
    
    raise ValueError(
        f"Unsupported accept type: {accept}. "
        "Supported types are: application/json, audio/wav, audio/mpeg"
    )