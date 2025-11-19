# News Scraping System - Setup and Usage Guide

## Overview

The news scraping system has been refactored for simplicity, reliability, and ease of testing. It scrapes Indian financial news from major RSS feeds and saves them to the database for sentiment analysis.

## Architecture

The refactored scraping system consists of:

1. **scraper_refactored.py** - Core scraping logic with 12 RSS feeds
2. **tasks_scraping.py** - Celery tasks for automated scraping
3. **management command** - Django command for manual scraping and testing

## Features

- ✅ **Synchronous & Reliable**: No async complexity, easier to debug
- ✅ **Robust Error Handling**: Retry logic, timeouts, detailed logging
- ✅ **12 RSS Feeds**: Major Indian financial news sources
- ✅ **Deduplication**: Hash-based duplicate detection
- ✅ **Manual Testing**: Django management command for testing
- ✅ **Automatic Scheduling**: Celery Beat integration
- ✅ **Content Extraction**: Title, summary, date, author, images, tags

## RSS Feed Sources

| Feed Key | Source | Category |
|----------|--------|----------|
| `economic_times_markets` | Economic Times - Markets | markets |
| `economic_times_stocks` | Economic Times - Stocks | stocks |
| `economic_times_industry` | Economic Times - Industry | industry |
| `business_standard_markets` | Business Standard - Markets | markets |
| `business_standard_companies` | Business Standard - Companies | companies |
| `livemint_markets` | LiveMint - Markets | markets |
| `livemint_companies` | LiveMint - Companies | companies |
| `moneycontrol_news` | MoneyControl - Latest News | general |
| `the_hindu_markets` | The Hindu - Markets | markets |
| `the_hindu_economy` | The Hindu - Economy | economy |
| `the_hindu_industry` | The Hindu - Industry | industry |
| `toi_business` | Times of India - Business | business |

## Manual Scraping (Django Management Command)

### List All Available Feeds
```bash
python manage.py scrape_news --list
```

### Test the Scraping System
```bash
# Test scraping without saving to database
python manage.py scrape_news --test --no-save

# Test scraping and save to database
python manage.py scrape_news --test
```

### Scrape a Specific Feed
```bash
# Scrape Economic Times Markets feed
python manage.py scrape_news --feed economic_times_markets

# Scrape and trigger sentiment analysis
python manage.py scrape_news --feed economic_times_markets --analyze
```

### Scrape All Feeds
```bash
# Scrape all configured feeds
python manage.py scrape_news

# Scrape all and trigger sentiment analysis
python manage.py scrape_news --analyze

# Scrape all without saving (for testing)
python manage.py scrape_news --no-save
```

## Automated Scraping (Celery)

### Celery Tasks

#### `scrape_all_news_sources`
Main scraping task that scrapes all 12 feeds and saves articles to database.

```python
from news_analyser.tasks_scraping import scrape_all_news_sources

# Trigger manually
result = scrape_all_news_sources.delay()
```

#### `scrape_single_feed`
Scrape a specific feed by key.

```python
from news_analyser.tasks_scraping import scrape_single_feed

# Scrape Economic Times Markets feed
result = scrape_single_feed.delay('economic_times_markets')
```

#### `analyze_recent_articles`
Analyze sentiment for recent unanalyzed articles.

```python
from news_analyser.tasks_scraping import analyze_recent_articles

# Analyze articles from last 24 hours
result = analyze_recent_articles.delay(hours=24)
```

#### `test_scraping_system`
Test task to verify scraping system is working.

```python
from news_analyser.tasks_scraping import test_scraping_system

# Run test
result = test_scraping_system.delay()
```

### Celery Beat Schedule

The scraping tasks are automatically scheduled:

**During Market Hours (9 AM - 4 PM IST, Mon-Fri):**
- Scrape every 30 minutes

**Off-Market Hours:**
- Scrape every 2 hours

**Sentiment Analysis:**
- Analyze pending articles every hour

**Cleanup:**
- Delete old unanalyzed articles weekly

## Running Celery Workers

### Start Celery Worker
```bash
celery -A blackbox worker -l info
```

### Start Celery Beat (Scheduler)
```bash
celery -A blackbox beat -l info
```

### Start Both Worker and Beat Together
```bash
celery -A blackbox worker -B -l info
```

## Testing the System

### 1. Quick Test (Management Command)
```bash
# Test without saving to database
python manage.py scrape_news --test --no-save

# Expected output:
# ✓ Successfully scraped X articles
# ✓ Sample article displayed
# TEST RESULT: PASSED ✓
```

### 2. Full System Test
```bash
# Scrape one feed and save to database
python manage.py scrape_news --feed economic_times_markets

# Check Django admin or shell to verify articles were saved
python manage.py shell
>>> from news_analyser.models import News
>>> News.objects.filter(is_analyzed=False).count()
```

### 3. Celery Test
```bash
# Start Celery worker
celery -A blackbox worker -l info

# In another terminal, trigger test task
python manage.py shell
>>> from news_analyser.tasks_scraping import test_scraping_system
>>> result = test_scraping_system.delay()
>>> result.get(timeout=30)
```

## Troubleshooting

### No Articles Scraped
1. Check internet connectivity
2. Verify RSS feed URLs are accessible (some may be blocked in certain regions)
3. Check logs for errors: `tail -f logs/celery.log`
4. Try manual scraping: `python manage.py scrape_news --test`

### Articles Not Saving to Database
1. Check database connection
2. Verify Source and Keyword models exist
3. Check for database errors in logs
4. Run migrations: `python manage.py migrate`

### Celery Tasks Not Running
1. Ensure Celery worker is running: `celery -A blackbox worker -l info`
2. Ensure Celery beat is running: `celery -A blackbox beat -l info`
3. Check Celery logs for errors
4. Verify Redis is running: `redis-cli ping`

### Sentiment Analysis Not Triggering
1. Ensure `analyze_article_sentiment` task is available
2. Check if new articles have `is_analyzed=False`
3. Manually trigger: `python manage.py scrape_news --analyze`

## Logging

All scraping activities are logged with detailed information:

- **INFO**: Successful operations, article counts, statistics
- **WARNING**: Non-critical issues like feed parsing warnings
- **ERROR**: Failed operations with stack traces

To view logs in real-time:
```bash
# Watch Django logs
tail -f logs/django.log

# Watch Celery logs
tail -f logs/celery.log
```

## Performance

- **Scraping Speed**: ~2-5 seconds per feed
- **Total Scraping Time**: ~30-60 seconds for all 12 feeds
- **Article Throughput**: ~100-300 articles per scraping run
- **Deduplication**: Hash-based, O(1) lookup

## Dependencies

Required Python packages:
- feedparser
- requests
- celery
- redis
- django

Install with:
```bash
pip install feedparser requests celery redis django
```

## Database Models

### News Model Fields Used
- `title`: Article title
- `link`: Article URL (unique)
- `content_summary`: Article summary/description
- `content`: Full article content (empty initially)
- `published_at`: Publication datetime
- `author`: Article author
- `image_url`: Featured image URL
- `tags`: Article tags (JSONField)
- `content_hash`: SHA256 hash for deduplication
- `source`: ForeignKey to Source model
- `keyword`: ForeignKey to Keyword model
- `is_analyzed`: Boolean flag for sentiment analysis
- `date`: Auto-populated timestamp

### Source Model
- `name`: Source name (e.g., "Economic Times - Markets")
- `url`: Source URL
- `is_active`: Active status flag

## Next Steps

After setting up the scraping system:

1. **Run Manual Test**: `python manage.py scrape_news --test`
2. **Start Celery Workers**: `celery -A blackbox worker -B -l info`
3. **Verify Automatic Scraping**: Wait for scheduled task or trigger manually
4. **Check Sentiment Analysis**: Ensure articles are being analyzed
5. **Monitor Logs**: Watch for errors or issues

## Support

For issues or questions:
1. Check logs: `tail -f logs/celery.log`
2. Run test command: `python manage.py scrape_news --test`
3. Verify dependencies are installed
4. Check Redis connection: `redis-cli ping`
