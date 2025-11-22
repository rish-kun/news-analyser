# Simplified, working Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and dependencies
# We need to do this as root before switching user
# But playwright install usually installs to /root/.cache/ms-playwright or similar
# We need to set PLAYWRIGHT_BROWSERS_PATH or install globally
ENV PLAYWRIGHT_BROWSERS_PATH=/app/pw-browsers
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH

# Install Playwright globally for root to use
RUN pip install playwright

# Install Playwright browsers
RUN playwright install --with-deps chromium

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
