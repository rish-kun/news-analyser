# Stage 1: Build stage
FROM python:3.11-slim-bullseye AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Stage 2: Final stage
FROM python:3.11-slim-bullseye

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=builder /app /app

RUN apt-get update && apt-get install -y --no-install-recommends libnss3 libnspr4 libdbus-1-3 libatk-bridge2.0-0 libgtk-3-0 libasound2 libgbm1 && rm -rf /var/lib/apt/lists/*
RUN pip install playwright && playwright install --with-deps

RUN useradd -m -d /home/appuser -s /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

ENV PATH="/home/appuser/.local/bin:${PATH}"

EXPOSE 8000
