# Screenshots Guide for News Analyser Alpha v1.0

This document outlines the screenshots needed to showcase the News Analyser application in the Pull Request.

## Required Screenshots

### 1. Login/Registration Page
**File**: `screenshots/01-login.png`
- Shows the authentication interface
- Demonstrates clean UI
- Captures the registration flow

### 2. Search Page (Main Interface)
**File**: `screenshots/02-search-page.png`
- Shows the main search interface
- Displays keyword and stock search options
- Shows user's watchlist stocks
- Captures the search form

### 3. Search Results Page
**File**: `screenshots/03-search-results.png`
- Shows news articles matching search query
- Displays sentiment scores with color coding
- Shows article summaries
- Demonstrates the results layout

### 4. News Detail Page
**File**: `screenshots/04-news-detail.png`
- Shows individual article view
- Displays full sentiment analysis:
  - Sentiment score
  - Confidence level
  - Explanation
  - Mentioned tickers
  - Impact timeline
- Shows article content
- Link to original source

### 5. Past Searches Page
**File**: `screenshots/05-past-searches.png`
- Shows user's search history
- Demonstrates search tracking feature

### 6. Watchlist Management
**File**: `screenshots/06-watchlist.png`
- Shows stock selection interface
- Displays available NSE stocks
- Shows sector organization

### 7. Admin Panel (Optional)
**File**: `screenshots/07-admin.png`
- Shows Django admin interface
- Displays news management
- Shows source configuration

### 8. Docker Containers Running
**File**: `screenshots/08-docker-ps.png`
- Terminal screenshot showing `docker-compose ps`
- All 5 services running (web, db, redis, celery, celery-beat)
- Shows health status

### 9. Test Coverage Report
**File**: `screenshots/09-test-coverage.png`
- Terminal screenshot showing test results
- Coverage report showing 80%+
- Test case count (58 tests)

### 10. Logs Demonstration
**File**: `screenshots/10-logs.png`
- Shows structured logging output
- Demonstrates error handling
- Shows Celery task execution

## How to Capture Screenshots

### Web Application Screenshots

1. **Start the application**:
   ```bash
   docker-compose up -d --build
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

2. **Open browser**: Navigate to http://localhost:8000

3. **Capture each page**:
   - Use browser's screenshot tool (F12 → Cmd/Ctrl+Shift+P → "Capture screenshot")
   - Or use OS screenshot tool (macOS: Cmd+Shift+4, Windows: Win+Shift+S)

4. **For each feature**:
   - Login page: Go to http://localhost:8000/accounts/login/
   - Search page: http://localhost:8000/search/
   - Search for "RELIANCE" to get results
   - Click on an article for detail view
   - Visit past searches page
   - Visit watchlist management

### Terminal Screenshots

1. **Docker containers**:
   ```bash
   docker-compose ps
   # Take screenshot showing all services running
   ```

2. **Run tests**:
   ```bash
   docker-compose exec web python manage.py test news_analyser --verbosity=2
   # Take screenshot of test output
   ```

3. **Coverage report**:
   ```bash
   docker-compose exec web coverage run --source='news_analyser' manage.py test news_analyser
   docker-compose exec web coverage report
   # Take screenshot of coverage summary
   ```

4. **Logs**:
   ```bash
   docker-compose logs web | tail -50
   docker-compose logs celery | tail -50
   # Take screenshots showing structured logging
   ```

## Adding Screenshots to PR

### Method 1: In PR Description

1. Upload screenshots to GitHub:
   - When editing the PR description, drag and drop images
   - GitHub will automatically host them

2. Add to PR description:
   ```markdown
   ## Screenshots

   ### Login Page
   ![Login](screenshots/01-login.png)

   ### Search Interface
   ![Search](screenshots/02-search-page.png)

   ### Search Results with Sentiment Scores
   ![Results](screenshots/03-search-results.png)

   ### Detailed News Analysis
   ![Detail](screenshots/04-news-detail.png)

   ### Test Coverage (80%+)
   ![Coverage](screenshots/09-test-coverage.png)
   ```

### Method 2: Add to Repository

1. Create screenshots directory:
   ```bash
   mkdir screenshots
   ```

2. Add screenshots to the directory

3. Update README.md to include them:
   ```markdown
   ## Screenshots

   <details>
   <summary>Click to view screenshots</summary>

   ### Search Interface
   ![Search](screenshots/02-search-page.png)

   ### Sentiment Analysis Results
   ![Results](screenshots/03-search-results.png)

   </details>
   ```

4. Commit and push:
   ```bash
   git add screenshots/
   git commit -m "docs: Add application screenshots"
   git push
   ```

### Method 3: Add to Wiki

1. Create a Wiki page on GitHub
2. Upload screenshots there
3. Link from README and PR description

## Screenshot Best Practices

1. **Use consistent dimensions**: 1920x1080 or 1440x900 for desktop
2. **Mobile screenshots**: If responsive, show mobile view too (375x667)
3. **Highlight key features**: Use annotations to point out important elements
4. **Clean data**: Use realistic test data, not Lorem Ipsum
5. **Show sentiment variety**: Capture positive, negative, and neutral examples
6. **Demonstrate key features**: Focus on sentiment analysis, multi-source news, watchlist

## Example PR Description with Screenshots

```markdown
# News Analyser Alpha v1.0 - Comprehensive Improvements

## Overview
This PR implements Phase 1 and Phase 2 improvements...

## Screenshots

### Main Search Interface
![Search Interface](https://user-images.githubusercontent.com/...)
*Users can search by keyword or select stocks from their watchlist*

### Sentiment Analysis Results
![Search Results](https://user-images.githubusercontent.com/...)
*News articles with AI-powered sentiment scores from -1 (negative) to +1 (positive)*

### Detailed Analysis
![News Detail](https://user-images.githubusercontent.com/...)
*Each article includes sentiment score, confidence, explanation, mentioned tickers, and impact timeline*

### Test Coverage
![Test Coverage](https://user-images.githubusercontent.com/...)
*58 test cases with 80%+ code coverage*

## Technical Improvements
...
```

## Tools for Screenshots

- **macOS**: Cmd+Shift+4 (area), Cmd+Shift+3 (full screen)
- **Windows**: Win+Shift+S (Snipping Tool)
- **Linux**: gnome-screenshot, Flameshot, or Spectacle
- **Browser Extensions**:
  - Awesome Screenshot (Chrome/Firefox)
  - FireShot (Chrome/Firefox)
- **Screen Recording**: For demo videos
  - macOS: QuickTime, Cmd+Shift+5
  - Windows: Xbox Game Bar (Win+G)
  - Linux: SimpleScreenRecorder, OBS

## Optional: Create a Demo Video

Consider creating a 2-3 minute demo video showing:
1. User registration
2. Searching for news
3. Viewing sentiment analysis
4. Managing watchlist
5. Checking past searches

Upload to YouTube or Loom and add link to PR.

---

**Note**: Make sure no sensitive data (API keys, personal information) is visible in screenshots!
