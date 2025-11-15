# Testing Guide - News Analyser

This document provides detailed information about the testing infrastructure for the News Analyser application.

## Test Suite Overview

The News Analyser has a comprehensive test suite with **58 test cases** achieving **80%+ code coverage**.

### Test Structure

```
news_analyser/tests/
├── __init__.py
├── test_models.py         # 22 test cases - Model logic and relationships
├── test_rss.py            # 14 test cases - RSS feed parsing
├── test_tasks.py          # 15 test cases - Celery task execution
└── test_integration.py    # 7 test cases - End-to-end workflows
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests
python manage.py test news_analyser

# Run specific test module
python manage.py test news_analyser.tests.test_models

# Run specific test class
python manage.py test news_analyser.tests.test_models.NewsModelTest

# Run specific test method
python manage.py test news_analyser.tests.test_models.NewsModelTest.test_news_creation

# Run with verbosity
python manage.py test news_analyser --verbosity=2
```

### Coverage Analysis

```bash
# Install coverage
pip install coverage

# Run tests with coverage
coverage run --source='news_analyser' manage.py test news_analyser

# View coverage report
coverage report

# Generate HTML coverage report
coverage html
# Open htmlcov/index.html in browser

# Check coverage for specific module
coverage report -m news_analyser/models.py
```

### Docker Testing

```bash
# Run tests in Docker container
docker-compose exec web python manage.py test news_analyser

# Run with coverage
docker-compose exec web coverage run --source='news_analyser' manage.py test news_analyser
docker-compose exec web coverage report
```

## Test Categories

### 1. Model Tests (`test_models.py`)

Tests all Django model functionality including:

- Model creation and validation
- String representations
- Relationships (ForeignKey, ManyToMany)
- Custom model methods
- Database indexes and constraints
- Model ordering

**Example Test:**
```python
def test_news_parse_news_does_not_duplicate(self):
    """Test that parse_news doesn't create duplicates for same link."""
    news_data = {
        'title': 'Article Title',
        'summary': 'Article summary',
        'link': 'https://example.com/article',
        'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
    }

    news1 = News.parse_news(news_data, self.keyword)
    news2 = News.parse_news(news_data, self.keyword)

    self.assertEqual(news1.id, news2.id)
    self.assertEqual(News.objects.count(), 1)
```

### 2. RSS Feed Tests (`test_rss.py`)

Tests RSS feed parsing and keyword matching:

- Feed fetching and parsing
- Keyword search (case-insensitive)
- Error handling for malformed feeds
- Missing field handling
- Feed source diversity
- Entry limiting

**Example Test:**
```python
@patch('news_analyser.rss.feedparser.parse')
def test_check_keywords_finds_matches(self, mock_parse):
    """Test that check_keywords finds articles matching keywords."""
    mock_feed = MagicMock()
    mock_feed.bozo = False
    mock_feed.entries = [
        {
            'title': 'Reliance Industries Q3 Results',
            'summary': 'Reliance reported excellent earnings',
            'link': 'https://example.com/article1',
            'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
        }
    ]
    mock_parse.return_value = mock_feed

    results = check_keywords(['RELIANCE'])

    self.assertIn('RELIANCE', results)
    self.assertGreater(len(results['RELIANCE']), 0)
```

### 3. Celery Task Tests (`test_tasks.py`)

Tests async task execution and error handling:

- Successful sentiment analysis
- JSON response parsing
- Simple float response parsing
- API error handling
- Retry logic with fallback API keys
- Sentiment score validation
- Ticker extraction
- Raw response storage

**Example Test:**
```python
@patch('news_analyser.tasks.genai.Client')
def test_analyse_news_task_success_json_response(self, mock_client_class):
    """Test successful sentiment analysis with JSON response."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "sentiment": 0.75,
        "confidence": 0.85,
        "explanation": "Major contract win",
        "tickers": ["TCS"],
        "impact_timeline": "short-term"
    })
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    result = analyse_news_task(self.news.id)

    self.assertEqual(result['status'], 'success')
    self.assertEqual(result['sentiment_score'], 0.75)
```

### 4. Integration Tests (`test_integration.py`)

Tests complete user workflows:

- User registration and profile creation
- Search-to-results flow
- Authentication requirements
- Watchlist management
- Search history tracking

**Example Test:**
```python
@patch('news_analyser.rss.feedparser.parse')
def test_complete_search_and_analysis_flow(self, mock_parse):
    """Test complete flow: login -> search -> view results."""
    user = User.objects.create_user('testuser', 'test@example.com', 'pass123')
    UserProfile.objects.create(user=user)
    self.client.login(username='testuser', password='pass123')

    # Mock RSS feed and search
    # Verify news creation and user association
```

## Test Fixtures

### Setting Up Test Data

```python
def setUp(self):
    """Common test setup."""
    self.keyword = Keyword.objects.create(name="TCS")
    self.source = Source.objects.create(
        id_name="ET",
        name="Economic Times",
        url="https://economictimes.indiatimes.com"
    )
    self.news = News.objects.create(
        title="Test Article",
        content_summary="Test summary",
        link="https://example.com/test",
        keyword=self.keyword,
        source=self.source
    )
```

### Test Isolation

Each test runs in its own transaction and is rolled back after completion. This ensures:
- No test pollution
- Predictable state
- Fast execution
- Database cleanliness

## Mocking External Dependencies

### Mocking Gemini API

```python
@patch('news_analyser.tasks.genai.Client')
def test_sentiment_analysis(self, mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "0.75"
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    # Test code here
```

### Mocking RSS Feeds

```python
@patch('news_analyser.rss.feedparser.parse')
def test_rss_parsing(self, mock_parse):
    mock_feed = MagicMock()
    mock_feed.bozo = False
    mock_feed.entries = [...]
    mock_parse.return_value = mock_feed

    # Test code here
```

## Writing New Tests

### Test Naming Convention

- Test methods start with `test_`
- Use descriptive names: `test_news_parse_news_creates_new_article`
- Class names end with `Test`: `NewsModelTest`

### Test Structure (AAA Pattern)

```python
def test_example(self):
    # Arrange: Set up test data
    user = User.objects.create_user('test', 'test@test.com', 'pass')

    # Act: Perform the action being tested
    profile = UserProfile.objects.create(user=user)

    # Assert: Verify the results
    self.assertEqual(profile.user, user)
```

### Best Practices

1. **One assertion per test** (when possible)
2. **Test edge cases**: empty values, None, invalid data
3. **Test error conditions**: exceptions, validation errors
4. **Use descriptive docstrings**
5. **Mock external dependencies**
6. **Keep tests isolated** (no dependencies between tests)
7. **Test both happy path and error paths**

### Example New Test

```python
class StockModelTest(TestCase):
    """Test cases for the Stock model."""

    def setUp(self):
        self.sector = Sector.objects.create(name="IT")

    def test_stock_unique_symbol_constraint(self):
        """Test that stock symbols must be unique."""
        Stock.objects.create(
            name="Tata Consultancy Services",
            symbol="TCS",
            sector=self.sector
        )

        # Attempting to create duplicate symbol should fail
        with self.assertRaises(IntegrityError):
            Stock.objects.create(
                name="Different Company",
                symbol="TCS",  # Duplicate
                sector=self.sector
            )
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Django CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: |
          python manage.py test news_analyser
      - name: Check coverage
        run: |
          coverage run --source='news_analyser' manage.py test news_analyser
          coverage report --fail-under=80
```

## Test Coverage Goals

- **Overall**: 80%+ coverage
- **Models**: 90%+ coverage
- **Views**: 85%+ coverage
- **Tasks**: 90%+ coverage
- **Utils**: 80%+ coverage

## Common Test Issues and Solutions

### Issue: Tests fail in Docker but pass locally

**Solution**: Ensure environment variables are set correctly in docker-compose.yml

### Issue: Celery tasks hang during tests

**Solution**: Use `@override_settings(CELERY_TASK_ALWAYS_EAGER=True)` to run tasks synchronously

### Issue: Database errors during tests

**Solution**: Use a separate test database (Django creates one automatically)

### Issue: Flaky tests (pass sometimes, fail other times)

**Solution**: Avoid time-dependent tests, use fixed timestamps, ensure proper test isolation

## Performance Testing

### Load Testing with Locust

```python
from locust import HttpUser, task, between

class NewsAnalyserUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login
        self.client.post("/accounts/login/", {
            "username": "testuser",
            "password": "testpass"
        })

    @task
    def search_news(self):
        self.client.post("/search/", {
            "search_type": "keyword",
            "keyword": "RELIANCE"
        })

    @task(2)  # Run twice as often
    def view_past_searches(self):
        self.client.get("/past-searches/")
```

## Debugging Failed Tests

```bash
# Run single failing test with debug output
python manage.py test news_analyser.tests.test_models.NewsModelTest.test_news_creation --verbosity=2

# Use pdb for interactive debugging
import pdb; pdb.set_trace()

# Check Django test database
python manage.py test news_analyser --keepdb  # Keep test database for inspection
```

## Test Maintenance

- Update tests when changing functionality
- Remove obsolete tests
- Refactor common setup into fixtures or base classes
- Keep test code as clean as production code
- Review coverage reports regularly

---

**Remember**: Good tests are the foundation of reliable software. Write tests for every new feature and bug fix!
