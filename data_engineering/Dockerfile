FROM python:3.9-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y wget

# Create required folder and download dataset
RUN mkdir -p ./data/processed && \
    wget "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx" \
         -O ./data/processed/online_retail.xlsx

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Python processing script
COPY data_processing.py .

# Run the data processing script
CMD ["python", "data_processing.py"]
