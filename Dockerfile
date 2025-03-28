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

# Expose port 5000 for Flask
EXPOSE 5000

# Set Python path
ENV PYTHONPATH=/var/app

# Switch to Gunicorn with longer timeout
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app", "--workers", "2", "--timeout", "600", "--max-requests", "1"]