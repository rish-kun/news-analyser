#!/bin/bash

# Screenshot Generator Script for News Analyser
# This script sets up the environment and captures screenshots

set -e

echo "=================================="
echo "News Analyser Screenshot Generator"
echo "=================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  WARNING: Please add your GEMINI_API_KEY to .env file"
    echo "⚠️  Press Enter to continue after updating .env, or Ctrl+C to exit"
    read
fi

# Set up database for screenshots (use SQLite for simplicity)
export DATABASE_URL="sqlite:///screenshot_db.sqlite3"
export DEBUG="True"
export SECRET_KEY="screenshot-secret-key-for-testing"

# Run migrations
echo "Running migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Create superuser (if needed)
echo "Creating superuser for admin screenshots..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✓ Superuser created')
else:
    print('✓ Superuser already exists')
EOF

# Start Django development server in background
echo "Starting Django development server..."
python manage.py runserver 8000 > /dev/null 2>&1 &
SERVER_PID=$!
echo "✓ Server started (PID: $SERVER_PID)"

# Wait for server to be ready
echo "Waiting for server to be ready..."
sleep 3

# Run screenshot capture script
echo ""
echo "Capturing screenshots..."
python capture_screenshots.py

# Kill the server
echo ""
echo "Stopping server..."
kill $SERVER_PID

echo ""
echo "=================================="
echo "✓ Screenshots generated successfully!"
echo "Check the screenshots/ directory"
echo "=================================="

# Deactivate virtual environment
deactivate
