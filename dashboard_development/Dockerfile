# dashboard_development/Dockerfile

# Use a Python base image
FROM python:3.9-bullseye 
# Set working directory inside the container
WORKDIR /app

# Copy requirements.txt and install Python dependencies
# 'requirements.txt' is now relative to the build context (dashboard_development/)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Streamlit app file
# 'dashboard.py' is now relative to the build context (dashboard_development/)
COPY dashboard.py .
# If you have other files/directories in dashboard_development that need to be copied:
COPY config.yaml .
# COPY data/ ./data/ # Example if you have a 'data' subdirectory in dashboard_development

# Expose the default Streamlit port
EXPOSE 8501

# Command to run your Streamlit app when the container starts
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]