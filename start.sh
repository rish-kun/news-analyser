#!/bin/bash

# News Analyser Docker Startup Script
# This script makes it easy to start the application

set -e

echo "=================================="
echo "News Analyser - Docker Startup"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running!${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Check if .env file exists, if not create from example
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found, creating from .env.example${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠ Please edit .env and add your GEMINI_API_KEY${NC}"
        echo -e "${YELLOW}⚠ Press Enter to continue with dummy key, or Ctrl+C to exit and edit .env${NC}"
        read
    else
        echo -e "${YELLOW}⚠ No .env.example found, using default values${NC}"
    fi
fi

# Stop any existing containers
echo ""
echo "Stopping any existing containers..."
docker-compose down 2>/dev/null || true

# Remove old volumes if requested
if [ "$1" == "--clean" ]; then
    echo -e "${YELLOW}Removing old volumes...${NC}"
    docker-compose down -v
fi

# Build and start containers
echo ""
echo "Building Docker images (this may take a few minutes)..."
docker-compose build

echo ""
echo "Starting containers..."
docker-compose up -d

# Wait for services to be healthy
echo ""
echo "Waiting for services to start..."
sleep 5

# Check container status
echo ""
echo "Container Status:"
docker-compose ps

# Show logs from web container
echo ""
echo "=================================="
echo "Checking web container logs..."
echo "=================================="
docker-compose logs --tail=20 web

# Final status check
echo ""
echo "=================================="
WEB_STATUS=$(docker inspect -f '{{.State.Status}}' news_analyser_web 2>/dev/null || echo "not found")
DB_STATUS=$(docker inspect -f '{{.State.Status}}' news_analyser_db 2>/dev/null || echo "not found")
REDIS_STATUS=$(docker inspect -f '{{.State.Status}}' news_analyser_redis 2>/dev/null || echo "not found")

if [ "$WEB_STATUS" == "running" ] && [ "$DB_STATUS" == "running" ] && [ "$REDIS_STATUS" == "running" ]; then
    echo -e "${GREEN}✓ All containers are running!${NC}"
    echo ""
    echo "Access the application at: http://localhost:8000"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker-compose logs -f web"
    echo "  - Stop containers: docker-compose down"
    echo "  - Restart: docker-compose restart"
    echo "  - Create superuser: docker-compose exec web python manage.py createsuperuser"
    echo ""
else
    echo -e "${RED}✗ Some containers failed to start${NC}"
    echo ""
    echo "Container statuses:"
    echo "  - Web: $WEB_STATUS"
    echo "  - Database: $DB_STATUS"
    echo "  - Redis: $REDIS_STATUS"
    echo ""
    echo "Check logs with: docker-compose logs"
    exit 1
fi

echo "=================================="
