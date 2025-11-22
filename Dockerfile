# Multi-stage build for optimized image size
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/logs /app/staticfiles && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Update PATH for appuser
ENV PATH=/home/appuser/.local/bin:$PATH

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

# Switch to non-root user
USER appuser

# Create logs directory with proper permissions
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["gunicorn", "blackbox.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
