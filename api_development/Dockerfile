# api_development/Dockerfile

# Use a Python base image. 'bullseye' is a Debian stable release, often more
# compatible with complex packages like Prophet than 'slim-buster'.
FROM python:3.9-bullseye

# Set working directory inside the container
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for models at the root level of the container.
# This matches the `MODEL_DIR = f"../models"` path in your app.py,
# assuming your app.py is copied to /app/app.py and models are at repo root.
RUN mkdir -p /models
# COPY models/ /models/  
# Copy your FastAPI application file
COPY app.py .

# Expose the port Uvicorn will listen on (default for FastAPI is 8000)
EXPOSE 8000

# Command to run your FastAPI application using Uvicorn
# --host 0.0.0.0 is crucial for running inside a Docker container
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]