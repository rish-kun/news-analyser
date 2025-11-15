# CLAUDE.md - AI Assistant Guide for News Analyser

## Project Overview

**News Analyser** is a Django-based financial news sentiment analysis platform focused on the Indian stock market. It aggregates news from multiple RSS feeds, analyzes sentiment using Google Gemini AI, and provides market impact scoring (-1 to +1) for stocks tracked by users.

**Core Purpose**: Help investors understand the sentiment and potential impact of news articles on their stock watchlist through automated AI-powered analysis.

**Production Domain**: `news-analyser.rish-kun.live`

---

## Quick Reference

### Tech Stack
- **Framework**: Django 5.1.6 (Python 3.13.3)
- **Database**: SQLite3 (dev) / PostgreSQL (prod)
- **Background Jobs**: Celery 5.4.0 with RabbitMQ
- **AI**: Google Gemini 2.5 Flash Preview
- **Frontend**: Django templates + Tailwind CSS + Vanilla JS
- **Containerization**: Docker + Docker Compose
- **Web Scraping**: browser-use (Playwright), feedparser

### Key Commands
```bash
# Development server
python manage.py runserver 0.0.0.0:8080

# Celery worker (required for sentiment analysis)
celery -A blackbox worker --loglevel=info

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Populate stock data
python manage.py populate_stocks Ticker_List_NSE_India.csv

# Run tests
python manage.py test

# Docker
docker-compose up --build  # Accessible on port 5959
```

### Environment Variables Required
```bash
SECRET_KEY=<django-secret-key>
GEMINI_API_KEY=<primary-gemini-key>
GEMINI_API_KEY_3=<fallback-gemini-key>
```

---

## Architecture

### Project Structure
```
news-analyser/
├── blackbox/              # Django project (settings, URLs, WSGI/ASGI, Celery config)
├── news_analyser/         # Main Django app (models, views, tasks, forms)
│   ├── models.py          # 6 models: Keyword, News, Source, Stock, Sector, UserProfile
│   ├── views.py           # 10+ views for search, analysis, user management
│   ├── tasks.py           # Celery task: analyse_news_task()
│   ├── urls.py            # App URL patterns (app_name='news_analyser')
│   ├── forms.py           # UserRegistrationForm, UserSettingsForm
│   ├── rss.py             # RSS feed sources (TOI, ET, The Hindu)
│   ├── br_use.py          # Browser automation for full article extraction
│   ├── prompts.py         # AI prompts for sentiment analysis
│   └── migrations/        # Database migrations
├── templates/             # Django templates (base.html, registration/, news_analyser/)
├── Dockerfile             # Python 3.13.3-bookworm with Playwright
├── docker-compose.yml     # Single service: blackbox (port 5959:8080)
├── requirements.txt       # 83 dependencies
└── manage.py              # Django management script
```

### Data Flow

**1. User Search Flow**
```
User submits search (keyword/stock)
    ↓
SearchView.post() processes request
    ↓
RSS feeds parsed (rss.py)
    ↓
News.parse_news() creates/retrieves News objects
    ↓
analyse_news_task.delay() queued for each article (Celery)
    ↓
Gemini API analyzes sentiment asynchronously
    ↓
impact_rating saved to News model
    ↓
User views results with sentiment scores
```

**2. Full Article Extraction Flow**
```
User clicks "Get Full Content"
    ↓
AJAX POST to /news_analysis/<id>/get_content/
    ↓
get_content() view triggers browser automation (br_use.py)
    ↓
Playwright scrapes article content
    ↓
Content saved to News.content field
    ↓
AJAX response updates UI
```

---

## Database Models

### Entity Relationships
```
User (Django Auth)
  ↓ OneToOne
UserProfile
  ├── stocks (ManyToMany) → Stock → Sector
  └── searches (ManyToMany) → Keyword
                                 ↓ ForeignKey
                               News → Source
```

### Model Details

**Keyword** (`news_analyser/models.py:5-8`)
- Represents search terms (stock names, general keywords)
- Fields: `name`, `create_date`
- Related: `news` (reverse FK), `stocks` (M2M), `users` (reverse M2M)

**News** (`news_analyser/models.py:10-56`)
- Central model for news articles
- Fields: `title`, `content_summary`, `content`, `date`, `link`, `keyword` (FK), `impact_rating`, `source` (FK)
- Key Methods:
  - `parse_news(news, kwd)`: Static factory method to create/retrieve news from RSS feed data
  - `get_content()`: Async method to scrape full article content via browser automation
- Impact Rating: Float field (-1.0 to 1.0) set by Gemini AI analysis

**UserProfile** (`news_analyser/models.py:74-78`)
- Extends Django User with app-specific data
- Fields: `user` (OneToOne), `preferences` (JSONField), `stocks` (M2M), `searches` (M2M)
- Preferences schema: `{'gemini_api_key': '<user-api-key>'}`
- Auto-created on user registration via `register()` view

**Stock** (`news_analyser/models.py:65-69`)
- NSE (National Stock Exchange of India) stocks
- Fields: `name`, `symbol`, `sector` (FK), `keywords` (M2M)
- Populated via `populate_stocks` management command from CSV

**Source** (`news_analyser/models.py:58-62`)
- News source identification
- Predefined sources: "ET" (Economic Times), "TOI" (Times of India), "TH" (The Hindu), "OTHER"
- Auto-assigned in `News.parse_news()` based on URL pattern matching

**Sector** (`news_analyser/models.py:71-72`)
- Stock categorization (Technology, Finance, Healthcare, etc.)
- Fields: `name`, `search_fields`

---

## Key Patterns & Conventions

### View Patterns

**Authentication**
```python
# Function-based views
@login_required
def search_result(request, news_id=None):
    # All users must be authenticated
    kwd = Keyword.objects.get(id=news_id)
    return render(request, 'news_analyser/result.html', context)

# Class-based views
class SearchView(LoginRequiredMixin, View):
    # Inherits login requirement
    def get(self, request): ...
    def post(self, request): ...
```

**Response Patterns**
```python
# Template rendering
return render(request, 'template.html', context)

# JSON responses (AJAX endpoints)
return JsonResponse({'total_news': count, 'analysed_news': analysed})

# Redirects
return redirect('news_analyser:search')
```

### Celery Task Pattern

**Task Definition** (`news_analyser/tasks.py:7-35`)
```python
from celery import shared_task

@shared_task
def analyse_news_task(news_id):
    """
    Analyze news sentiment using Gemini API.

    Args:
        news_id: Primary key of News object

    Returns:
        impact_rating (float) or "Error" string
    """
    try:
        news = News.objects.get(id=news_id)
        # AI processing...
        news.impact_rating = float(rating)
        news.save()
        return news.impact_rating
    except News.DoesNotExist:
        print(f"News item with id {news_id} not found.")
        return "Error"
    except Exception as e:
        print(f"Error analyzing news: {e}")
        return "Error"
```

**Task Execution** (from views)
```python
# Queue task for background execution
analyse_news_task.delay(news_id)

# Never block on task results in views
# Use AJAX polling to check completion status
```

### RSS Feed Parsing Pattern

**Feed Sources** (`news_analyser/rss.py:1-16`)
```python
sources = {
    'TOI': [
        'https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms',
        # ... 4 more TOI feeds
    ],
    'ET': [
        'https://economictimes.indiatimes.com/rssfeedstopstories.cms',
        # ... 5 more ET feeds
    ],
    'TH': [
        'https://www.thehindu.com/news/national/?service=rss',
        # ... 4 more TH feeds
    ]
}
```

**Parsing Implementation** (`news_analyser/views.py:23-43`)
```python
import feedparser
from .models import News, Keyword, Source

# Parse all feeds for a keyword
for feed in sources['TOI'] + sources['ET'] + sources['TH']:
    news_feed = feedparser.parse(feed)
    for news in news_feed.entries:
        # Create or retrieve News object
        obj = News.parse_news(news, kwd)
        # Queue sentiment analysis
        analyse_news_task.delay(obj.id)
```

### Model Factory Pattern

**News.parse_news()** (`news_analyser/models.py:24-56`)
```python
@staticmethod
def parse_news(news, kwd):
    """
    Create or retrieve News object from RSS feed entry.

    Pattern: get_or_create with post-creation initialization
    """
    obj, created = News.objects.get_or_create(
        link=news['link'],
        keyword=kwd,
        defaults={
            'title': news['title'],
            'content_summary': news['summary']
        }
    )

    if created:
        # Only set fields for new objects
        try:
            obj.date = parsedate_to_datetime(news['published'])
        except:
            obj.date = timezone.now()

        # Auto-assign source based on URL
        if "economc" in obj.link and "times" in obj.link:
            obj.source = Source.objects.get(id_name="ET")
        elif "times" in obj.link and "india" in obj.link:
            obj.source = Source.objects.get(id_name="TOI")
        elif "thehindu" in obj.link:
            obj.source = Source.objects.get(id_name="TH")
        else:
            obj.source = Source.objects.get(id_name="OTHER")

        obj.save()

    return obj
```

### Async Pattern (Content Extraction)

**Async Method in Model** (`news_analyser/models.py:20-22`)
```python
async def get_content(self):
    """Fetch full article content using browser automation."""
    from .br_use import get_news
    content = await get_news(self.link)
    return content
```

**Synchronous Caller in View** (`news_analyser/views.py:147-168`)
```python
import asyncio

@csrf_exempt  # AJAX endpoint
def get_content(request, news_id):
    if request.method == "POST":
        news = News.objects.get(id=news_id)

        # Run async function in sync context
        content = asyncio.run(news.get_content())

        news.content = content
        news.save()

        return JsonResponse({
            'message': 'Content fetched successfully',
            'content': content
        })
```

### Error Handling Patterns

**Defensive Parsing**
```python
# Always provide fallbacks for external data
try:
    date = parsedate_to_datetime(news['published'])
except:
    date = timezone.now()  # Use current time as fallback
```

**API Retry Pattern** (`news_analyser/tasks.py:16-27`)
```python
while True:
    try:
        analysis = client.models.generate_content(...)
        break  # Success, exit loop
    except genai.errors.ClientError:
        # Fallback to alternate API key
        alt_api_key = os.getenv("GEMINI_API_KEY")
        client2 = genai.Client(api_key=alt_api_key)
        analysis = client2.models.generate_content(...)
        break
```

**Database Not Found Handling**
```python
try:
    obj = Model.objects.get(id=some_id)
except Model.DoesNotExist:
    # Log error, don't crash
    print(f"Model with id {some_id} not found.")
    return redirect('fallback_view')
```

---

## Common Tasks

### Adding a New View

1. **Define view function/class** in `news_analyser/views.py`
   ```python
   from django.contrib.auth.decorators import login_required

   @login_required
   def my_new_view(request):
       context = {'data': ...}
       return render(request, 'news_analyser/my_template.html', context)
   ```

2. **Add URL pattern** in `news_analyser/urls.py`
   ```python
   urlpatterns = [
       # ...
       path('my-route/', views.my_new_view, name='my_view'),
   ]
   ```

3. **Create template** in `templates/news_analyser/my_template.html`
   ```django
   {% extends 'base.html' %}
   {% block title %}My Page{% endblock %}
   {% block content %}
       <!-- Content here -->
   {% endblock %}
   ```

4. **Reference in templates**
   ```django
   <a href="{% url 'news_analyser:my_view' %}">Link Text</a>
   ```

### Adding a New Model Field

1. **Update model** in `news_analyser/models.py`
   ```python
   class News(models.Model):
       # ... existing fields
       new_field = models.CharField(max_length=200, null=True, blank=True)
   ```

2. **Create migration**
   ```bash
   python manage.py makemigrations
   # Review the generated migration file
   ```

3. **Apply migration**
   ```bash
   python manage.py migrate
   ```

4. **Update admin** (optional) in `news_analyser/admin.py`
   ```python
   @admin.register(News)
   class NewsAdmin(admin.ModelAdmin):
       list_display = ['title', 'date', 'keyword', 'new_field']
   ```

### Adding a New Celery Task

1. **Define task** in `news_analyser/tasks.py`
   ```python
   from celery import shared_task

   @shared_task
   def my_background_task(arg1, arg2):
       """Task description."""
       try:
           # Processing logic
           result = process_data(arg1, arg2)
           return result
       except Exception as e:
           print(f"Error in my_background_task: {e}")
           return None
   ```

2. **Call from view**
   ```python
   from .tasks import my_background_task

   def some_view(request):
       # Queue task asynchronously
       my_background_task.delay(value1, value2)
       # Don't wait for result
       return redirect('success_page')
   ```

3. **Test Celery is running**
   ```bash
   celery -A blackbox worker --loglevel=info
   # Should see task registered in output
   ```

### Adding RSS Feed Sources

1. **Update sources dict** in `news_analyser/rss.py`
   ```python
   sources = {
       'TOI': [...],
       'ET': [...],
       'TH': [...],
       'NEW_SOURCE': [
           'https://newssite.com/rss/business.xml',
           'https://newssite.com/rss/markets.xml',
       ]
   }
   ```

2. **Add Source to database** (via Django shell or migration)
   ```python
   from news_analyser.models import Source
   Source.objects.create(
       id_name="NS",
       name="New Source",
       url="https://newssite.com"
   )
   ```

3. **Update URL matching** in `News.parse_news()` (`models.py:46-54`)
   ```python
   if "newssite" in obj.link:
       obj.source = Source.objects.get(id_name="NS")
   ```

### Adding User Preferences

User preferences are stored as JSON in `UserProfile.preferences` field.

1. **Update form** in `news_analyser/forms.py`
   ```python
   class UserSettingsForm(forms.Form):
       new_preference = forms.CharField(required=False)
   ```

2. **Update view** in `news_analyser/views.py`
   ```python
   @login_required
   def user_settings(request):
       profile = request.user.profile

       if request.method == "POST":
           form = UserSettingsForm(request.POST)
           if form.is_valid():
               # Save to preferences JSON
               profile.preferences['new_preference'] = form.cleaned_data['new_preference']
               profile.save()

       # Initialize form with current value
       initial = {'new_preference': profile.preferences.get('new_preference', '')}
       form = UserSettingsForm(initial=initial)
   ```

3. **Update template** (`templates/news_analyser/user_settings.html`)
   ```django
   <input type="text" name="new_preference" value="{{ form.new_preference.value }}">
   ```

---

## Development Workflows

### Initial Setup (New Developer)

```bash
# 1. Clone repository
git clone <repo-url>
cd news-analyser

# 2. Create .env file
cp .env.example .env
# Edit .env and add required keys

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Populate stock data
python manage.py populate_stocks Ticker_List_NSE_India.csv

# 8. Start development server
python manage.py runserver

# 9. Start Celery worker (separate terminal)
celery -A blackbox worker --loglevel=info

# 10. Access application
# http://localhost:8000
```

### Docker Setup

```bash
# 1. Create .env file first
cp .env.example .env
# Edit with API keys

# 2. Build and run
docker-compose up --build

# 3. Access application
# http://localhost:5959

# 4. Run commands in container
docker-compose exec blackbox python manage.py createsuperuser
docker-compose exec blackbox python manage.py populate_stocks Ticker_List_NSE_India.csv
```

### Testing Workflow

```bash
# Run all tests
python manage.py test

# Run specific test class
python manage.py test news_analyser.tests.UserAuthTests

# Run specific test method
python manage.py test news_analyser.tests.UserAuthTests.test_user_registration

# Run with verbosity
python manage.py test --verbosity=2
```

**Current Test Coverage**: Only authentication tests exist. Need to add tests for:
- RSS feed parsing
- News model methods
- Celery tasks
- View logic
- Form validation

### Git Workflow

```bash
# Current development branch
git checkout claude/claude-md-mhzw8qvs9hy785jj-015KLrYF8jKHp298TXPYcAdN

# Create feature branch (from main)
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Commit changes
git add .
git commit -m "Clear description of changes"

# Push to remote
git push -u origin feature/your-feature-name

# After PR merge
git checkout main
git pull origin main
git branch -d feature/your-feature-name
```

### Database Workflow

```bash
# Check current migrations
python manage.py showmigrations

# Create new migration
python manage.py makemigrations

# Preview SQL
python manage.py sqlmigrate news_analyser 0008

# Apply migrations
python manage.py migrate

# Rollback migration
python manage.py migrate news_analyser 0007

# Reset database (development only)
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
python manage.py populate_stocks Ticker_List_NSE_India.csv
```

---

## Important Gotchas

### 1. Celery Must Be Running
**Problem**: Sentiment analysis won't happen if Celery worker is not running.

**Symptom**: News articles appear with `impact_rating = 0.0` and never update.

**Solution**:
```bash
# Always run Celery worker during development
celery -A blackbox worker --loglevel=info
```

**Check**: Look for "Task news_analyser.tasks.analyse_news_task received" in Celery output.

### 2. RabbitMQ/Redis Dependency
**Problem**: Celery requires RabbitMQ as message broker (configured in settings).

**Current Configuration**: `CELERY_BROKER_URL = 'amqp://localhost'` (RabbitMQ)

**Note**: README mentions Redis, but current implementation uses RabbitMQ. Ensure RabbitMQ is running:
```bash
# Install RabbitMQ (Ubuntu/Debian)
sudo apt-get install rabbitmq-server
sudo systemctl start rabbitmq-server

# Or use Docker
docker run -d --name rabbitmq -p 5672:5672 rabbitmq:3
```

### 3. Environment Variables
**Problem**: Missing environment variables cause crashes.

**Required Variables**:
- `SECRET_KEY`: Django secret (critical for production)
- `GEMINI_API_KEY`: Primary API key for sentiment analysis
- `GEMINI_API_KEY_3`: Fallback key for browser automation

**Best Practice**: Always copy `.env.example` to `.env` and populate before running.

### 4. Playwright Browser Installation
**Problem**: `browser-use` library requires Playwright browsers installed.

**Error**: "Executable doesn't exist" when trying to fetch full article content.

**Solution**:
```bash
playwright install chromium
# Or in Docker (already in Dockerfile)
RUN playwright install chromium
```

### 5. CSRF Exemption on AJAX
**Issue**: `/news_analysis/<id>/get_content/` view is marked `@csrf_exempt`.

**Security Risk**: This bypasses CSRF protection. Safe only because:
1. View requires POST method
2. User must be logged in (via session)
3. Only modifies data owned by user

**Better Approach**: Include CSRF token in AJAX requests instead.

### 6. Print Statements vs Logging
**Issue**: Error handling uses `print()` statements instead of proper logging.

**Current Pattern**:
```python
except Exception as e:
    print(f"Error: {e}")  # Goes to console only
```

**Recommended**:
```python
import logging
logger = logging.getLogger(__name__)

except Exception as e:
    logger.error(f"Error analyzing news {news_id}: {e}", exc_info=True)
```

### 7. Duplicate Search Logic
**Issue**: `SearchView.post()` has duplicate code blocks for "keyword" vs "stock" search types.

**Location**: `news_analyser/views.py:69-100` and `102-133`

**Refactor Opportunity**: Extract common logic into helper method.

### 8. Source URL Matching
**Issue**: Source assignment relies on substring matching in URLs.

**Fragile Pattern** (`models.py:46-54`):
```python
if "economc" in obj.link and "times" in obj.link:  # Typo: "economc"
    obj.source = Source.objects.get(id_name="ET")
```

**Risk**: URL changes break source assignment, defaults to "OTHER".

**Improvement**: Use proper URL parsing and domain matching.

### 9. Async in Sync Context
**Issue**: `News.get_content()` is async but called from sync view with `asyncio.run()`.

**Current Pattern**:
```python
content = asyncio.run(news.get_content())
```

**Limitation**: Blocks the request until browser automation completes (can be slow).

**Better Approach**: Make this a Celery task for true async execution.

### 10. Static Files in Production
**Issue**: Django's default static file handling doesn't work in production.

**Current Setup**: No static file configuration in `docker-compose.yml` (volume defined but unused).

**Required for Production**:
```python
# settings.py
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Collect static files
python manage.py collectstatic

# Serve with Nginx or WhiteNoise
```

---

## Security Considerations

### Current Issues (Development Mode)

1. **DEBUG = True** (line `blackbox/settings.py:26`)
   - Must be `False` in production
   - Leaks sensitive information on errors

2. **ALLOWED_HOSTS = ['*']** (line `blackbox/settings.py:28`)
   - Too permissive
   - Production should specify exact domains

3. **SECRET_KEY in Environment**
   - Good: Uses environment variable
   - Risk: Ensure `.env` is in `.gitignore` (currently is)

4. **CSRF Exemption**
   - `@csrf_exempt` on `get_content()` view
   - Consider removing and adding CSRF token to AJAX

5. **User-Supplied API Keys**
   - UserProfile.preferences stores user's own Gemini API keys
   - Good: Users can use their own quota
   - Risk: Keys stored in plain text in database
   - Consider: Encryption at rest for API keys

6. **No Rate Limiting**
   - No throttling on expensive operations (browser automation, AI calls)
   - Consider: django-ratelimit for protection

### Best Practices for Production

```python
# settings.py production checklist
DEBUG = False
ALLOWED_HOSTS = ['news-analyser.rish-kun.live']
SECRET_KEY = os.getenv('SECRET_KEY')  # Long random string
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # ... PostgreSQL config
    }
}

# Logging
LOGGING = {
    # Proper logging configuration
}
```

---

## Future Improvements

### High Priority

1. **Comprehensive Testing**
   - Add tests for News.parse_news()
   - Test Celery tasks (use CELERY_TASK_ALWAYS_EAGER)
   - Integration tests for RSS parsing
   - View tests for all endpoints

2. **Proper Logging**
   - Replace all `print()` statements
   - Configure Django logging with file handlers
   - Log Celery task execution and failures

3. **Error Handling**
   - Add custom error pages (404, 500)
   - Implement graceful degradation for API failures
   - User-friendly error messages

4. **Refactor Duplicate Code**
   - Extract common search logic in SearchView
   - Create helper functions for RSS parsing

5. **Async Refactor**
   - Convert `get_content()` view to Celery task
   - Add task progress tracking
   - Implement WebSocket for real-time updates

### Medium Priority

6. **Performance Optimization**
   - Add database indexes on frequently queried fields
   - Implement select_related/prefetch_related
   - Cache RSS feed results (short TTL)

7. **Feature Completion**
   - Finish SectorView implementation
   - Complete scraper.py integration
   - Add external news APIs (NewsAPI.org, etc.)

8. **Enhanced Sentiment Analysis**
   - Store analysis metadata (confidence, keywords extracted)
   - Track sentiment over time (trending)
   - Aggregated stock sentiment score

9. **User Experience**
   - Add HTMX/Alpine.js (mentioned in README but not implemented)
   - Real-time updates without page refresh
   - Better loading states

### Low Priority

10. **Stock Price Integration**
    - Fetch live stock prices
    - Correlate sentiment with price movements
    - Historical analysis

11. **Email Notifications**
    - Alert users to high-impact news
    - Daily digest of watchlist news

12. **API Endpoints**
    - REST API for external access
    - API authentication (JWT)
    - Rate limiting

---

## Code Style Guide

### Python (PEP 8)

**Naming Conventions**:
- Classes: `PascalCase` (e.g., `SearchView`, `UserProfile`)
- Functions/Methods: `snake_case` (e.g., `get_content`, `parse_news`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `GEMINI_API_KEY`)
- Private methods: `_leading_underscore` (e.g., `_helper_method`)

**Imports**:
```python
# Standard library
import os
import asyncio
from datetime import datetime

# Django
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Third-party
import feedparser
from celery import shared_task

# Local
from .models import News, Keyword
from .tasks import analyse_news_task
```

**Docstrings**:
```python
def complex_function(arg1, arg2):
    """
    Brief description of function.

    Args:
        arg1: Description of first argument
        arg2: Description of second argument

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception occurs
    """
    pass
```

### Django Templates

**Template Inheritance**:
```django
{% extends 'base.html' %}

{% block title %}Page Title{% endblock %}

{% block content %}
    <!-- Page content -->
{% endblock %}

{% block extra_js %}
    <script>
        // Page-specific JavaScript
    </script>
{% endblock %}
```

**URL Reversing**:
```django
{# Always use named URLs #}
<a href="{% url 'news_analyser:search' %}">Search</a>
<a href="{% url 'news_analyser:news_analysis' news.id %}">Details</a>
```

**Template Variables**:
```django
{# Use descriptive variable names #}
{{ news.title }}
{{ stock.symbol }}
{{ user.profile.preferences.gemini_api_key }}
```

### JavaScript

**Vanilla JS Patterns** (current approach):
```javascript
document.addEventListener('DOMContentLoaded', function() {
    // Initialization code

    // Event listeners
    document.getElementById('btn').addEventListener('click', function(e) {
        e.preventDefault();
        // Handler logic
    });
});
```

**Fetch API for AJAX**:
```javascript
fetch('/api/endpoint/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({data: 'value'})
})
.then(response => response.json())
.then(data => {
    // Handle response
})
.catch(error => console.error('Error:', error));
```

### Git Commit Messages

**Format**:
```
<type>: <subject>

<optional body>

<optional footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat: add sector-based news filtering

fix: correct source URL matching for Economic Times

refactor: extract RSS parsing into separate utility function

test: add tests for News.parse_news() method

docs: update README with Celery setup instructions
```

---

## Useful Resources

### Django Documentation
- Models: https://docs.djangoproject.com/en/5.1/topics/db/models/
- Views: https://docs.djangoproject.com/en/5.1/topics/http/views/
- Templates: https://docs.djangoproject.com/en/5.1/topics/templates/
- Forms: https://docs.djangoproject.com/en/5.1/topics/forms/
- Authentication: https://docs.djangoproject.com/en/5.1/topics/auth/

### Celery
- Getting Started: https://docs.celeryq.dev/en/stable/getting-started/introduction.html
- Django Integration: https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html

### Google Gemini API
- Python SDK: https://ai.google.dev/gemini-api/docs/quickstart?lang=python
- Model documentation: https://ai.google.dev/gemini-api/docs/models/gemini

### Libraries
- feedparser: https://feedparser.readthedocs.io/
- browser-use: https://github.com/browser-use/browser-use
- Playwright: https://playwright.dev/python/

### NSE India
- Stock data source: https://www.nseindia.com/
- Market watch: https://www.nseindia.com/market-data/live-equity-market

---

## Questions & Support

### Common Questions

**Q: Why is sentiment analysis not working?**
A: Ensure Celery worker is running and `GEMINI_API_KEY` is set in `.env`.

**Q: How do I add support for a new news source?**
A: Add RSS feed URL to `rss.py`, create Source object in database, update URL matching in `News.parse_news()`.

**Q: Can users use their own API keys?**
A: Yes! Users can set their personal Gemini API key in Settings page, stored in `UserProfile.preferences`.

**Q: How to reset the database in development?**
A: Delete `db.sqlite3`, run migrations, recreate superuser, and repopulate stocks.

**Q: Why is the full article content not loading?**
A: Ensure Playwright browsers are installed (`playwright install chromium`) and `GEMINI_API_KEY_3` is set.

**Q: How to deploy to production?**
A: Switch to PostgreSQL, set `DEBUG=False`, configure static files, set up Nginx, enable SSL, use Gunicorn/uWSGI, run Celery as systemd service.

### Getting Help

1. **Check logs**: Django server output, Celery worker logs
2. **Review migrations**: `python manage.py showmigrations`
3. **Django shell**: `python manage.py shell` for debugging
4. **Admin panel**: `http://localhost:8000/admin` to inspect data

### Reporting Issues

When reporting bugs:
1. Include error messages (full traceback)
2. Specify environment (local/Docker, Python version)
3. List steps to reproduce
4. Share relevant logs (Django, Celery)
5. Check if Celery worker is running

---

## Changelog

**2025-11-15**: Initial CLAUDE.md creation
- Comprehensive codebase analysis completed
- Documented all models, views, tasks, patterns
- Identified improvement areas and gotchas
- Provided development workflows and common tasks

---

## Appendix: File Reference

### Core Application Files

| File | Purpose | Key Contents |
|------|---------|--------------|
| `blackbox/settings.py` | Django configuration | Database, Celery, apps, middleware, templates, static |
| `blackbox/urls.py` | Root URL routing | Admin, auth, news_analyser app inclusion |
| `blackbox/celery.py` | Celery configuration | Broker, result backend, task discovery |
| `news_analyser/models.py` | Database models | 6 models with relationships and methods |
| `news_analyser/views.py` | Request handlers | 10+ views for search, analysis, user management |
| `news_analyser/tasks.py` | Background jobs | `analyse_news_task()` for Gemini API calls |
| `news_analyser/urls.py` | App URL patterns | 12 routes for app functionality |
| `news_analyser/forms.py` | Form definitions | Registration and settings forms |
| `news_analyser/rss.py` | RSS feed sources | TOI, ET, TH feed URLs |
| `news_analyser/br_use.py` | Browser automation | Playwright-based content extraction |
| `news_analyser/prompts.py` | AI prompts | Sentiment analysis prompt templates |
| `templates/base.html` | Base template | Navigation, messages, common layout |
| `requirements.txt` | Python dependencies | 83 packages with versions |
| `Dockerfile` | Container image | Python 3.13.3 with Playwright |
| `docker-compose.yml` | Multi-container orchestration | Single service, port mapping |
| `manage.py` | Django CLI | Management command entry point |

### Management Commands

| Command | File | Purpose |
|---------|------|---------|
| `populate_stocks` | `news_analyser/management/commands/populate_stocks.py` | Import stocks from CSV file |

### Migrations (news_analyser)

| Migration | Description |
|-----------|-------------|
| `0001_initial` | Created Keyword, News models |
| `0002_news_impact_rating` | Added sentiment score field |
| `0003_source_rename` | Created Source model |
| `0004_news_source` | Added FK to Source |
| `0005_alter_news_content` | Made content nullable |
| `0006_sector_stock_user` | Created Sector, Stock, UserProfile |
| `0007_alter_userprofile` | Modified searches relationship |

### Template Structure

```
templates/
├── base.html                       # Base layout with nav
├── registration/
│   ├── login.html                  # Login form
│   ├── register.html               # User registration
│   └── logged_out.html             # Logout confirmation
└── news_analyser/
    ├── search.html                 # Main search interface
    ├── result.html                 # Search results display
    ├── news_analysis.html          # Detailed news view
    ├── add_stocks.html             # Manage watchlist
    ├── past_searches.html          # Search history
    ├── user_settings.html          # User preferences
    └── loading.html                # Loading state
```

---

**End of CLAUDE.md**

*This document is intended for AI assistants working with the News Analyser codebase. Keep it updated as the project evolves.*
