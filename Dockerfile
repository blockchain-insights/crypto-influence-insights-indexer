# Use the official Python 3.10 image
FROM python:3.10

# Set the working directory
WORKDIR /crypto-influence-insights-indexer

# Copy the requirements file into the working directory
COPY requirements.txt requirements.txt

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    build-essential \
    && apt-get clean

# Upgrade pip, setuptools, and wheel
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .
