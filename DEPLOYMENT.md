# Deployment Guide - News Analyser

This guide covers deploying the News Analyser platform to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Redis Setup](#redis-setup)
5. [Application Deployment](#application-deployment)
6. [Celery Workers](#celery-workers)
7. [Web Server Configuration](#web-server-configuration)
8. [SSL/TLS Setup](#ssltls-setup)
9. [Monitoring & Logging](#monitoring--logging)
10. [Backup Strategy](#backup-strategy)

## Prerequisites

- Ubuntu 20.04 LTS or later
- Python 3.11+
- PostgreSQL 12+
- Redis 5.0+
- Nginx
- Supervisor (for process management)
- Domain name (optional, for SSL)

## Environment Setup

### 1. Create Application User

```bash
sudo adduser newsanalyser
sudo usermod -aG sudo newsanalyser
su - newsanalyser
```

### 2. Install System Dependencies

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip
sudo apt install -y postgresql postgresql-contrib
sudo apt install -y redis-server
sudo apt install -y nginx
sudo apt install -y supervisor
sudo apt install -y git
```

### 3. Clone Repository

```bash
cd /home/newsanalyser
git clone https://github.com/rish-kun/news-analyser.git
cd news-analyser
```

### 4. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Database Setup

### 1. Create PostgreSQL Database

```bash
sudo -u postgres psql

CREATE DATABASE news_analyser;
CREATE USER newsanalyser_user WITH PASSWORD 'your_secure_password';
ALTER ROLE newsanalyser_user SET client_encoding TO 'utf8';
ALTER ROLE newsanalyser_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE newsanalyser_user SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE news_analyser TO newsanalyser_user;
\q
```

### 2. Configure Database in .env

```bash
cp .env.example .env
nano .env
```

Update with your database credentials:
```env
DATABASE_URL=postgresql://newsanalyser_user:your_secure_password@localhost:5432/news_analyser
```

### 3. Run Migrations

```bash
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 4. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

## Redis Setup

### 1. Configure Redis

```bash
sudo nano /etc/redis/redis.conf
```

Update:
```
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### 2. Start and Enable Redis

```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
sudo systemctl status redis-server
```

## Application Deployment

### 1. Configure Production Settings

Update `blackbox/settings.py`:

```python
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

### 2. Install Gunicorn

```bash
pip install gunicorn
```

### 3. Create Gunicorn Configuration

```bash
nano /home/newsanalyser/news-analyser/gunicorn_config.py
```

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
accesslog = "/home/newsanalyser/news-analyser/logs/gunicorn_access.log"
errorlog = "/home/newsanalyser/news-analyser/logs/gunicorn_error.log"
loglevel = "info"
```

## Celery Workers

### 1. Create Supervisor Configuration for Celery Worker

```bash
sudo nano /etc/supervisor/conf.d/newsanalyser-celery-worker.conf
```

```ini
[program:newsanalyser-celery-worker]
command=/home/newsanalyser/news-analyser/venv/bin/celery -A blackbox worker -l info
directory=/home/newsanalyser/news-analyser
user=newsanalyser
numprocs=1
stdout_logfile=/home/newsanalyser/news-analyser/logs/celery_worker.log
stderr_logfile=/home/newsanalyser/news-analyser/logs/celery_worker_error.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
priority=998
```

### 2. Create Supervisor Configuration for Celery Beat

```bash
sudo nano /etc/supervisor/conf.d/newsanalyser-celery-beat.conf
```

```ini
[program:newsanalyser-celery-beat]
command=/home/newsanalyser/news-analyser/venv/bin/celery -A blackbox beat -l info
directory=/home/newsanalyser/news-analyser
user=newsanalyser
numprocs=1
stdout_logfile=/home/newsanalyser/news-analyser/logs/celery_beat.log
stderr_logfile=/home/newsanalyser/news-analyser/logs/celery_beat_error.log
autostart=true
autorestart=true
startsecs=10
priority=999
```

### 3. Create Supervisor Configuration for Gunicorn

```bash
sudo nano /etc/supervisor/conf.d/newsanalyser-gunicorn.conf
```

```ini
[program:newsanalyser-gunicorn]
command=/home/newsanalyser/news-analyser/venv/bin/gunicorn blackbox.wsgi:application -c /home/newsanalyser/news-analyser/gunicorn_config.py
directory=/home/newsanalyser/news-analyser
user=newsanalyser
autostart=true
autorestart=true
stdout_logfile=/home/newsanalyser/news-analyser/logs/gunicorn_supervisor.log
stderr_logfile=/home/newsanalyser/news-analyser/logs/gunicorn_supervisor_error.log
```

### 4. Start All Services

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
sudo supervisorctl status
```

## Web Server Configuration

### 1. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/newsanalyser
```

```nginx
upstream newsanalyser {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 10M;

    location /static/ {
        alias /home/newsanalyser/news-analyser/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /home/newsanalyser/news-analyser/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://newsanalyser;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
}
```

### 2. Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/newsanalyser /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL/TLS Setup

### 1. Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

### 2. Obtain SSL Certificate

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 3. Auto-renewal

```bash
sudo systemctl status certbot.timer
```

Test renewal:
```bash
sudo certbot renew --dry-run
```

## Monitoring & Logging

### 1. Set Up Log Rotation

```bash
sudo nano /etc/logrotate.d/newsanalyser
```

```
/home/newsanalyser/news-analyser/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 newsanalyser newsanalyser
    sharedscripts
    postrotate
        supervisorctl restart all > /dev/null
    endscript
}
```

### 2. Monitor with Supervisor

```bash
# Check all processes
sudo supervisorctl status

# View logs
sudo supervisorctl tail -f newsanalyser-celery-worker
sudo supervisorctl tail -f newsanalyser-gunicorn

# Restart services
sudo supervisorctl restart all
```

### 3. Set Up Monitoring (Optional)

Install Prometheus Node Exporter:
```bash
wget https://github.com/prometheus/node_exporter/releases/download/v1.5.0/node_exporter-1.5.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.5.0.linux-amd64.tar.gz
sudo cp node_exporter-1.5.0.linux-amd64/node_exporter /usr/local/bin/
sudo useradd -rs /bin/false node_exporter
```

## Backup Strategy

### 1. Database Backups

Create backup script:
```bash
nano /home/newsanalyser/backup_db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/newsanalyser/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="news_analyser_${DATE}.sql"

mkdir -p $BACKUP_DIR

pg_dump -U newsanalyser_user -h localhost news_analyser > "${BACKUP_DIR}/${FILENAME}"

gzip "${BACKUP_DIR}/${FILENAME}"

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

Make executable:
```bash
chmod +x /home/newsanalyser/backup_db.sh
```

Add to crontab:
```bash
crontab -e

# Add:
0 2 * * * /home/newsanalyser/backup_db.sh
```

### 2. Application Backups

```bash
# Backup application files
tar -czf news_analyser_app_$(date +%Y%m%d).tar.gz /home/newsanalyser/news-analyser
```

## Performance Tuning

### 1. PostgreSQL Tuning

```bash
sudo nano /etc/postgresql/12/main/postgresql.conf
```

```
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 8MB
min_wal_size = 1GB
max_wal_size = 4GB
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### 2. Redis Tuning

```bash
sudo nano /etc/redis/redis.conf
```

```
maxmemory 512mb
maxmemory-policy allkeys-lru
save ""
```

## Health Checks

Create health check script:
```bash
nano /home/newsanalyser/health_check.sh
```

```bash
#!/bin/bash

# Check if Gunicorn is running
curl -f http://localhost:8000/admin/ > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Gunicorn is down!"
    sudo supervisorctl restart newsanalyser-gunicorn
fi

# Check if Celery worker is running
supervisorctl status newsanalyser-celery-worker | grep RUNNING > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Celery worker is down!"
    sudo supervisorctl restart newsanalyser-celery-worker
fi

# Check Redis
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Redis is down!"
    sudo systemctl restart redis-server
fi
```

Add to crontab:
```bash
*/5 * * * * /home/newsanalyser/health_check.sh
```

## Troubleshooting

### Common Issues

1. **502 Bad Gateway**
   - Check if Gunicorn is running: `sudo supervisorctl status newsanalyser-gunicorn`
   - Check logs: `sudo supervisorctl tail -f newsanalyser-gunicorn stderr`

2. **Celery Tasks Not Processing**
   - Check worker status: `sudo supervisorctl status newsanalyser-celery-worker`
   - Check Redis: `redis-cli ping`
   - View worker logs: `tail -f /home/newsanalyser/news-analyser/logs/celery_worker.log`

3. **Database Connection Errors**
   - Check PostgreSQL status: `sudo systemctl status postgresql`
   - Verify credentials in `.env`
   - Check database exists: `sudo -u postgres psql -l`

4. **Static Files Not Loading**
   - Run: `python manage.py collectstatic`
   - Check Nginx configuration
   - Verify file permissions

## Security Checklist

- [ ] DEBUG = False in production
- [ ] Strong SECRET_KEY set
- [ ] Database password is strong and unique
- [ ] ALLOWED_HOSTS configured correctly
- [ ] SSL certificate installed and auto-renewing
- [ ] Firewall configured (UFW recommended)
- [ ] PostgreSQL not exposed to internet
- [ ] Redis not exposed to internet
- [ ] Regular security updates applied
- [ ] Backup system tested and working
- [ ] Monitoring and alerting configured
- [ ] Log rotation configured
- [ ] Rate limiting enabled

## Post-Deployment

1. **Test the application**
   - Access via HTTPS
   - Test API endpoints
   - Verify Celery tasks are running
   - Check admin panel

2. **Monitor performance**
   - Watch logs for errors
   - Monitor Redis memory usage
   - Check database performance
   - Monitor disk space

3. **Schedule maintenance**
   - Weekly: Review logs
   - Monthly: Update dependencies
   - Quarterly: Security audit
   - Annually: Infrastructure review

---

**For production support, contact the Wall Street Club development team.**
