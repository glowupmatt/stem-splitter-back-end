FROM python:3.9-slim

LABEL maintainer="Matthew Nicholson"
LABEL version="1.0"
LABEL description="Demucs audio separation service"

WORKDIR /var/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directories for Demucs output
RUN mkdir -p separated/htdemucs

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Set Python path
ENV PYTHONPATH=/var/app

# Switch to Gunicorn with port 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app", "--workers", "2", "--timeout", "600"]