# Stem Splitter Back End

This repository contains the backend server for the Stem Splitter application. The server processes audio files to split them into stems using Demucs, PyTorch, Torchaudio, and FFmpeg. The processed audio files are stored in AWS S3 buckets, and downloadable links are returned for the frontend to display the audio waves.

Front End Code:
 - https://github.com/glowupmatt/splitter-fe

## Features

- **Audio Processing**: Utilizes Demucs with PyTorch, Torchaudio, and FFmpeg to split audio files into stems.
- **AWS S3 Integration**: Stores processed audio files in AWS S3 buckets and provides downloadable links.
- **Backend Server**: Handles requests from the frontend and processes the audio files.

## Technologies Used

- **Python**: Main programming language for the backend server.
- **Demucs**: Deep learning model for music source separation.
- **PyTorch**: Machine learning framework used for running Demucs.
- **Torchaudio**: Audio processing package for PyTorch.
- **FFmpeg**: Multimedia framework for handling audio files.
- **AWS S3**: Storage service for storing and retrieving processed audio files.
- **Docker**: Used for containerizing the application.

## ENV File
For this project I used AWS but you can replace with whatever cloud service you decide to go with.

 - AWS_ACCESS_KEY_ID
 - AWS_SECRET_ACCESS_KEY
 - AWS_BUCKET_NAME
 - AWS_DEFAULT_REGION

## API Endpoints

- **/api/separate**: Endpoint to upload audio files for processing and returns the new stems.
- **/api/download_stem**: Endpoint to allow the user download the individual stem.
- **/api/clean_bucket**: Endpoint to delete all the files in the S3 Bucket.

## Getting Started

To get started with the project, follow these steps:

1. **Clone the Repository**:
    ```sh
    git clone https://github.com/glowupmatt/stem-splitter-back-end.git
    cd stem-splitter-back-end
    ```

2. **Build and Run the Docker Container**:
    ```sh
    docker build -t stem-splitter-backend .
    docker run -p 8000:8000 stem-splitter-backend
    ```

3. **Install Dependencies**:
    If you prefer to run the server locally, you can install the dependencies using pip:
    ```sh
    pip install -r requirements.txt
    ```

4. **Run the Server**:
    ```sh
    python main.py
    ```
