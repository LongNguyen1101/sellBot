# Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# RUN apt-get update && apt-get upgrade -y && apt-get clean

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your source code
COPY . .

# Command to run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
