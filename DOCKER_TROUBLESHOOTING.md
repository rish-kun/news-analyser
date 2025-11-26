# Docker Troubleshooting Guide

This guide helps you resolve common Docker issues with the News Analyser application.

## Quick Start (Works 99% of the time)

```bash
# 1. Make sure Docker is running
docker --version
docker-compose --version

# 2. Start everything with one command
./start.sh

# 3. Access the app
# Open http://localhost:8000 in your browser
```

## Common Issues and Solutions

### Issue 1: "Docker is not running"

**Error**: `Cannot connect to the Docker daemon`

**Solution**:
```bash
# Start Docker Desktop
# On Mac: Open Docker Desktop from Applications
# On Windows: Start Docker Desktop from Start menu
# On Linux: sudo systemctl start docker

# Verify Docker is running
docker ps
```

### Issue 2: "Port already in use"

**Error**: `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution**:
```bash
# Find what's using port 8000
# On Mac/Linux:
lsof -i :8000
# On Windows:
netstat -ano | findstr :8000

# Kill the process or stop Docker containers
docker-compose down

# Or change the port in docker-compose.yml:
# ports:
#   - "8001:8000"  # Use port 8001 instead
```

### Issue 3: "Container exits immediately"

**Error**: Container starts then stops

**Solution**:
```bash
# Check logs to see what went wrong
docker-compose logs web

# Common causes:
# 1. Missing environment variables
cp .env.example .env
# Edit .env and add GEMINI_API_KEY

# 2. Database not ready
# Wait longer or check db logs
docker-compose logs db

# 3. Migration errors
# Run migrations manually
docker-compose exec web python manage.py migrate
```

### Issue 4: "Build failed"

**Error**: `ERROR [build X/Y]` or similar

**Solution**:
```bash
# Clean everything and rebuild
docker-compose down -v
docker system prune -a
docker-compose build --no-cache

# If still fails, check:
# 1. Internet connection (needs to download packages)
# 2. Disk space (run: df -h or docker system df)
# 3. Docker Desktop resources (increase memory/CPU in settings)
```

### Issue 5: "Database connection refused"

**Error**: `could not connect to server: Connection refused`

**Solution**:
```bash
# Make sure database container is running
docker-compose ps

# Restart database
docker-compose restart db

# Wait for database to be ready
docker-compose logs db | grep "ready to accept connections"

# Check database healthcheck
docker inspect news_analyser_db | grep -A 5 Health
```

### Issue 6: "Permission denied"

**Error**: `PermissionError: [Errno 13] Permission denied: '/app/logs'`

**Solution**:
```bash
# Fix permissions
chmod -R 777 logs/ staticfiles/ media/

# Or rebuild with clean slate
docker-compose down -v
docker-compose up -d --build
```

### Issue 7: "Migrations not applied"

**Error**: `no such table: news_analyser_news`

**Solution**:
```bash
# Run migrations manually
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# Verify migrations
docker-compose exec web python manage.py showmigrations
```

### Issue 8: "Celery worker not starting"

**Error**: Celery container exits or shows errors

**Solution**:
```bash
# Check Celery logs
docker-compose logs celery

# Restart Celery
docker-compose restart celery

# Common issue: Redis not ready
docker-compose logs redis

# Test Redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### Issue 9: "502 Bad Gateway / Connection refused"

**Error**: Browser shows "502 Bad Gateway" or cannot connect

**Solution**:
```bash
# Check if web container is actually running
docker-compose ps web

# Check web container logs
docker-compose logs --tail=50 web

# Restart web container
docker-compose restart web

# Wait a bit longer - initial startup takes 30-60 seconds
sleep 30
curl http://localhost:8000

# Check if gunicorn is running inside container
docker-compose exec web ps aux | grep gunicorn
```

### Issue 10: "ModuleNotFoundError"

**Error**: `ModuleNotFoundError: No module named 'django'` or similar

**Solution**:
```bash
# Rebuild the image to reinstall dependencies
docker-compose build --no-cache web

# Verify requirements.txt exists
ls -la requirements.txt

# Check if dependencies installed
docker-compose exec web pip list
```

## Complete Reset (Nuclear Option)

If nothing else works:

```bash
# 1. Stop everything
docker-compose down

# 2. Remove all volumes (WARNING: deletes database data)
docker-compose down -v

# 3. Remove all images
docker system prune -a

# 4. Rebuild from scratch
docker-compose build --no-cache

# 5. Start fresh
docker-compose up -d

# 6. Check logs
docker-compose logs -f
```

## Verification Checklist

After starting, verify everything works:

```bash
# 1. Check all containers are running
docker-compose ps
# Should show: web, db, redis, celery all "Up"

# 2. Check database is healthy
docker-compose exec db psql -U news_user -d news_analyser -c "SELECT 1;"
# Should return: 1

# 3. Check Redis is working
docker-compose exec redis redis-cli ping
# Should return: PONG

# 4. Check web is responding
curl http://localhost:8000
# Should return HTML

# 5. Check Celery can connect
docker-compose exec celery celery -A blackbox inspect ping
# Should return: pong

# 6. Check logs for errors
docker-compose logs --tail=100 | grep -i error
```

## Getting Help

If you're still stuck:

1. **Check logs**: `docker-compose logs > debug.log` and review
2. **Check container status**: `docker-compose ps`
3. **Check resource usage**: `docker stats`
4. **Check Docker version**: `docker --version` (need 20.10+ and compose 1.29+)
5. **Check system resources**: Ensure you have at least 4GB RAM and 10GB disk space

## Environment Variable Issues

If the app starts but doesn't work properly:

```bash
# Check environment variables are set
docker-compose exec web env | grep -E "DATABASE_URL|GEMINI_API_KEY|REDIS_URL"

# Should show:
# DATABASE_URL=postgresql://news_user:news_password@db:5432/news_analyser
# CELERY_BROKER_URL=redis://redis:6379/0
# GEMINI_API_KEY=your-key-here

# If missing, check your .env file
cat .env

# Or set them directly in docker-compose.yml environment section
```

## Performance Issues

If containers are slow:

```bash
# 1. Increase Docker Desktop resources
# Docker Desktop → Settings → Resources
# Recommended: 4 CPU, 4GB RAM

# 2. Check resource usage
docker stats

# 3. Reduce Celery workers
# Edit docker-compose.yml:
# command: celery -A blackbox worker --concurrency=1

# 4. Check disk space
docker system df
```

## Development vs Production

For development:
```bash
# Use docker-compose.dev.yml overlay
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

For production:
```bash
# Use regular docker-compose.yml
docker-compose up -d

# Set proper environment variables:
# - DEBUG=False
# - Strong SECRET_KEY
# - Real GEMINI_API_KEY
```

## Still Not Working?

Create an issue with:
1. Output of `docker-compose logs > logs.txt`
2. Output of `docker-compose ps`
3. Your OS and Docker version
4. Contents of your .env file (WITHOUT sensitive data)

---

**Remember**: First time startup takes 2-3 minutes to download images and build. Be patient!
