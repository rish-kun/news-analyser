# Simplified, working Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# The base image already has most things, but we might need some specific ones
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
# The base image includes dependencies, but we ensure browsers are installed
RUN playwright install chromium

# Copy project files
COPY . .

# Fix permissions
RUN chown -R appuser:appuser /app

# Create necessary directories
RUN mkdir -p /app/logs /app/staticfiles /app/media && \
    chmod -R 777 /app/logs /app/staticfiles /app/media

# Expose port
EXPOSE 8000

# Default command
CMD ["gunicorn", "blackbox.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
