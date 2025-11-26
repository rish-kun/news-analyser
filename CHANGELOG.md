# Changelog

All notable changes to the News Analyser project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-alpha] - 2025-11-15

### Added - Phase 1: Foundation & Cleanup

#### Environment & Configuration
- Integrated `django-environ` for environment variable management
- Created comprehensive `.env.example` with all required configuration variables
- Configured PostgreSQL as primary database (replacing SQLite)
- Set up Redis as Celery broker and result backend
- Implemented structured logging with console and rotating file handlers
  - Separate log files: `django.log`, `celery.log`, `errors.log`
  - Configurable log levels via `LOG_LEVEL` environment variable
- Added proper `.gitignore` entries for sensitive files and SQLite database

#### Docker Infrastructure
- Created production-ready `docker-compose.yml` with 5 services:
  - PostgreSQL 15 database
  - Redis 7 for Celery
  - Django web application with Gunicorn
  - Celery worker
  - Celery Beat scheduler
- Implemented multi-stage Dockerfile for optimized image size
- Added health checks for all services
- Configured persistent volumes for data retention
- Created `docker-compose.dev.yml` for development environment

#### Code Organization
- Removed duplicate `scrapper.py` file (kept `scraper.py`)
- Removed test files from root: `resp.json`, `db.sqlite3`
- Created `news_analyser/utils/` directory for utility modules
- Moved utility scripts to proper locations
- Created custom exceptions module (`exceptions.py`) with domain-specific errors:
  - `GeminiAPIError`, `GeminiRateLimitError`, `GeminiAuthenticationError`
  - `RSSFeedError`, `ContentExtractionError`, `InvalidSentimentScoreError`
- Added comprehensive docstrings to all modules and functions

#### Error Handling & Logging
- Implemented structured logging throughout application
- Added try-except blocks for all external API calls
- Created retry logic for transient failures with exponential backoff
- Implemented task-level error handling in Celery tasks
- Added detailed error logging with stack traces

### Added - Phase 2: Feature Completion & Enhancement

#### RSS Feed Sources (7+ new sources added)
- Added **MoneyControl** RSS feeds (4 feeds)
- Added **Business Standard** RSS feeds (4 feeds)
- Added **LiveMint** RSS feeds (4 feeds)
- Added **CNBC TV18** RSS feeds (2 feeds)
- Added additional **Economic Times** market feeds (2 feeds)
- **Total**: 27+ RSS feeds from 7 major Indian financial news sources

#### Database Optimization
- Added database indexes on frequently queried fields:
  - News: `(keyword_id, date)`, `(link)`, `(impact_rating)`, `(source_id, date)`
  - Keyword: `(name)`, `(create_date)`, `(name, create_date)`
  - Stock: `(symbol)`, `(sector_id, symbol)`
  - Source: `(id_name)`
  - UserProfile: `(user_id)`
- Made `link` field unique in News model to prevent duplicates
- Added `created_at` and `updated_at` timestamp fields to News model
- Implemented proper model ordering (most recent first)

#### Enhanced Sentiment Analysis
- **Structured Gemini API Output**: Updated prompts to request JSON responses
- **New News Model Fields**:
  - `sentiment_explanation`: Detailed reasoning for sentiment score
  - `sentiment_confidence`: Model's confidence level (0-1)
  - `mentioned_tickers`: List of stock symbols mentioned in article
  - `raw_gemini_response`: Full API response for debugging
  - `created_at`, `updated_at`: Automatic timestamps
- **Enhanced Sentiment Analysis**:
  - Sentiment score with confidence level
  - 2-3 sentence explanation of reasoning
  - Automatic extraction of mentioned stock tickers
  - Impact timeline classification (immediate/short/medium/long-term)
- **Improved Prompt Engineering**:
  - Detailed sentiment scoring guidelines
  - Financial market context
  - Specific instructions for Indian stock market
  - Structured JSON output format

#### Celery Task Improvements
- Implemented task retry logic with exponential backoff (max 3 retries)
- Added task timeout limits (5 minutes max, 4.5 minutes soft limit)
- Multiple API key fallback for rate limiting
- Task progress updates via `self.update_state()`
- Comprehensive error handling and logging
- JSON response parsing with fallback to simple float
- Validation of sentiment score ranges

#### News Parsing Enhancements
- Improved `News.parse_news()` method to use `link` as unique identifier
- Automatic source detection for 7+ news sources
- Better error handling for date parsing
- Created sources automatically via `get_or_create`

### Added - Testing Infrastructure

#### Comprehensive Test Suite (58 test cases)
- **Model Tests** (`test_models.py`): 22 test cases
  - Keyword, UserProfile, News, Sector, Stock, Source models
  - Model creation, relationships, ordering
  - Custom model methods (parse_news, get_news)
  - Database constraints and validation
  - Source auto-detection logic

- **RSS Feed Tests** (`test_rss.py`): 14 test cases
  - Keyword matching (case-insensitive)
  - Feed parsing and error handling
  - Malformed feed handling
  - Missing field handling
  - Feed source diversity verification
  - Entry limiting functionality

- **Celery Task Tests** (`test_tasks.py`): 15 test cases
  - Successful sentiment analysis (JSON and simple float)
  - Sentiment score validation
  - API error handling
  - Retry logic with fallback keys
  - Ticker extraction
  - Raw response storage
  - Negative and neutral sentiment handling

- **Integration Tests** (`test_integration.py`): 7 test cases
  - User registration and profile creation
  - Complete search-to-results workflow
  - Authentication requirements
  - Watchlist management
  - Search history tracking

#### Test Coverage
- Achieved 80%+ overall test coverage
- Comprehensive mocking of external dependencies (Gemini API, RSS feeds)
- Test isolation with Django's TestCase
- Coverage reporting with `coverage.py`

### Changed

- **Database**: Migrated from SQLite to PostgreSQL
- **Celery Broker**: Changed from RabbitMQ (`amqp://localhost`) to Redis
- **Settings**: Replaced `python-dotenv` with `django-environ` for better configuration management
- **Time Zone**: Updated to Asia/Kolkata for Celery tasks
- **Celery Configuration**: Added JSON serialization, task tracking, and timeout limits

### Fixed

- Fixed typo in News model source detection: `"economc"` → `"economictimes"`
- Fixed duplicate news creation by using `link` as unique identifier
- Fixed date parsing errors by adding try-except blocks
- Fixed source creation errors by using `get_or_create` instead of `get`
- Improved error handling in RSS feed parsing

### Security

- Removed hardcoded API keys from settings
- Added `.env` to `.gitignore`
- Removed `db.sqlite3` from version control
- Implemented proper secret key management
- Added security checks via `python manage.py check --deploy`

### Documentation

- Created comprehensive `README.md` with:
  - Feature overview
  - Tech stack details
  - Quick start guide
  - Usage instructions
  - Troubleshooting guide
  - Contributing guidelines

- Created detailed `TESTING.md` with:
  - Test suite overview
  - Running tests guide
  - Coverage analysis
  - Writing new tests guide
  - CI/CD examples
  - Debugging tips

- Created `CHANGELOG.md` (this file)

- Updated `.env.example` with:
  - All required environment variables
  - Detailed comments and descriptions
  - Example values

### Dependencies

#### Added
- `django-environ==0.11.2` - Environment variable management
- `psycopg2-binary==2.9.10` - PostgreSQL adapter
- `coverage==7.6.10` - Test coverage analysis
- `flake8==7.1.1` - Code linting
- `black==24.10.0` - Code formatting
- `gunicorn==21.2.0` - Production WSGI server

### Performance

- Optimized database queries with proper indexes
- Reduced N+1 query issues with select_related/prefetch_related (where applicable)
- Implemented entry limiting in RSS feed processing (default 50 per feed)
- Added database-level constraints for data integrity

### Developer Experience

- Added structured logging for better debugging
- Implemented comprehensive error messages
- Created detailed test documentation
- Added code organization improvements
- Implemented proper exception handling

---

## Upcoming in v1.1

### Planned Features
- [ ] UI improvements with Tailwind CSS
- [ ] HTMX for dynamic content updates
- [ ] Alpine.js for reactive components
- [ ] Sentiment trend charts
- [ ] Email notifications for watchlist stocks
- [ ] Advanced filtering and sorting
- [ ] Export functionality (CSV, PDF)

### Planned Improvements
- [ ] Query optimization for large datasets
- [ ] Caching layer for frequently accessed data
- [ ] WebSocket support for real-time updates
- [ ] API endpoints for programmatic access
- [ ] Historical sentiment tracking
- [ ] Portfolio impact calculator

---

## Release Notes

### Alpha v1.0 Highlights

This is the first alpha release of News Analyser, focusing on establishing a solid foundation with:

✅ **Complete Backend Implementation**
- 7+ RSS feed sources (27+ individual feeds)
- AI-powered sentiment analysis with structured output
- Robust error handling and retry logic
- Production-ready Docker deployment

✅ **Comprehensive Testing**
- 58 test cases covering all critical functionality
- 80%+ code coverage
- Integration tests for complete workflows
- Mocked external dependencies

✅ **Production-Ready Infrastructure**
- PostgreSQL database with optimizations
- Celery with Redis for async processing
- Structured logging and monitoring
- Docker containerization

✅ **Enhanced Data Quality**
- Sentiment score with confidence level
- Detailed explanations for analysis
- Automatic ticker extraction
- Impact timeline classification

### Known Limitations

- UI is basic (Django templates without modern CSS framework)
- No real-time updates (requires page refresh)
- Limited to RSS feeds (no direct API integrations beyond Gemini)
- No historical sentiment trends or charts
- No email/SMS notifications

These limitations will be addressed in future releases.

---

**Note**: This changelog will be updated with each release. For detailed commit history, see the Git log.
