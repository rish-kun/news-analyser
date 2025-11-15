# Stage 1: Build stage
FROM python:3.9-slim-buster AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Stage 2: Final stage
FROM python:3.9-slim-buster

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=builder /app /app

RUN useradd -m -d /home/appuser -s /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
