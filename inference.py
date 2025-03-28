import os
import torch
import json
from model_package.model.htdemucs import HTDemucs

def model_fn(model_dir):
    """Load the model for inference"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Initialize model with same params as training
    model = HTDemucs(
        sources=["drums", "bass", "other", "vocals"],
        audio_channels=2,
    )
    
    # Load saved model weights
    model.load_state_dict(torch.load(
        os.path.join(model_dir, 'model.pth'),
        map_location=device
    ))
    model.eval()
    return model.to(device)

def input_fn(request_body, request_content_type):
    """Deserialize and preprocess the request"""
    if request_content_type == 'application/json':
        input_data = json.loads(request_body)
        # Convert input audio to tensor
        audio_tensor = torch.tensor(input_data['audio'])
        return audio_tensor
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model):
    """Model inference"""
    with torch.no_grad():
        output = model(input_data)
    return output

def output_fn(prediction, accept):
    """Return prediction"""
    if accept == 'application/json':
        # Convert output tensor to list
        separated_audio = prediction.cpu().numpy().tolist()
        return json.dumps({'separated_stems': separated_audio})
    raise ValueError(f"Unsupported accept type: {accept}")