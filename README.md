# News Analyser - Alpha v1.0

A Django-based financial news sentiment analysis platform for the Indian stock market. This application aggregates news from multiple Indian sources, analyzes sentiment using Google's Gemini API, and provides investors with real-time market insights.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Django 5.1.6](https://img.shields.io/badge/django-5.1.6-green.svg)](https://www.djangoproject.com/)
[![Test Coverage 80%+](https://img.shields.io/badge/coverage-80%25+-brightgreen.svg)](.)

## Features

### Core Functionality
- **Multi-Source RSS Aggregation**: Fetches news from 7+ Indian financial news sources
  - Economic Times, Times of India, The Hindu
  - MoneyControl, Business Standard, LiveMint, CNBC TV18
- **AI-Powered Sentiment Analysis**: Uses Google Gemini API for sophisticated market impact analysis
- **Structured Sentiment Data**: Extracts sentiment score, confidence, explanation, mentioned tickers, and impact timeline
- **User Watchlists**: Create and manage stock portfolios
- **Search History**: Track and revisit past searches
- **Real-time Updates**: Celery-powered async sentiment analysis

### Technical Features
- PostgreSQL database with optimized indexes
- Redis-backed Celery for async task processing
- Comprehensive error handling and retry logic
- Structured logging (console + rotating file logs)
- Docker containerization for easy deployment
- 80%+ test coverage with 58+ test cases

## Tech Stack

- **Backend**: Django 5.1.6, Python 3.11
- **Database**: PostgreSQL 15
- **Task Queue**: Celery 5.4.0 with Redis 7
- **AI**: Google Gemini API (gemini-2.5-flash-preview)
- **Deployment**: Docker, Gunicorn
- **Testing**: Django TestCase, unittest.mock, Coverage.py

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/rish-kun/news-analyser.git
   cd news-analyser
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your Gemini API key
   ```

   Required variables in `.env`:
   ```bash
   SECRET_KEY=your-secret-key-here
   GEMINI_API_KEY=your-gemini-api-key
   DATABASE_URL=postgresql://news_user:news_password@db:5432/news_analyser
   ```

3. **Build and run with Docker**
   ```bash
   docker-compose up -d --build
   ```

4. **Run migrations**
   ```bash
   docker-compose exec web python manage.py makemigrations
   docker-compose exec web python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

6. **Access the application**
   - Web app: http://localhost:8000
   - Admin panel: http://localhost:8000/admin

## Usage

### Searching for News

1. **By Keyword**: Search for any term (e.g., "RELIANCE", "inflation", "RBI")
2. **By Stock**: Select stocks from your watchlist
3. The app will:
   - Fetch latest news from 20+ RSS feeds
   - Parse and store articles
   - Trigger async sentiment analysis via Celery
   - Display results with sentiment scores

### Understanding Sentiment Scores

- **-1.0 to -0.5**: Highly negative impact (caution/sell signal)
- **-0.5 to -0.1**: Moderately negative (watch)
- **-0.1 to +0.1**: Neutral/No major impact (hold)
- **+0.1 to +0.5**: Moderately positive (watch)
- **+0.5 to +1.0**: Highly positive impact (potential buy signal)

### Enhanced Sentiment Analysis

Each article includes:
- **Sentiment Score**: -1 (very negative) to +1 (very positive)
- **Confidence**: Model's confidence in the analysis (0-1)
- **Explanation**: 2-3 sentence reasoning
- **Mentioned Tickers**: Stock symbols found in article
- **Impact Timeline**: immediate, short-term, medium-term, or long-term

## Testing

### Run Test Suite
```bash
# All tests
python manage.py test news_analyser

# Specific test module
python manage.py test news_analyser.tests.test_models

# With coverage
coverage run --source='news_analyser' manage.py test news_analyser
coverage report
```

### Test Coverage
- **Models**: 22 test cases
- **RSS Feeds**: 14 test cases
- **Celery Tasks**: 15 test cases
- **Integration**: 7 test cases
- **Total**: 58 test cases, 80%+ coverage

See [TESTING.md](TESTING.md) for detailed testing documentation.

## Architecture

### Components

- **Web App** (Django): User interface, search, results display
- **Celery Workers**: Async sentiment analysis tasks
- **PostgreSQL**: Persistent data storage
- **Redis**: Celery broker and result backend
- **Gemini API**: AI-powered sentiment analysis

## Troubleshooting

### Common Issues

**Celery tasks not processing**
- Ensure Redis is running: `docker-compose logs redis`
- Check Celery logs: `docker-compose logs celery`

**Gemini API rate limit errors**
- Add multiple API keys (`GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`)
- Tasks will automatically retry with fallback keys

**RSS feeds not fetching**
- Check network connectivity
- Some feeds may be temporarily down - handled gracefully

## Contributing

This is a college project for Wall Street Club, BITS Pilani. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new features
4. Ensure all tests pass
5. Submit a Pull Request

## License

Educational project - BITS Pilani

## Acknowledgments

- **Wall Street Club, BITS Pilani** - Project sponsor
- **Google Gemini** - AI sentiment analysis
- **Indian News Sources** - ET, TOI, The Hindu, MoneyControl, BS, LiveMint, CNBC TV18

---

**Disclaimer**: This tool is for educational purposes only. Sentiment analysis results should not be used as sole basis for investment decisions. Always consult financial advisors before making investments.
