# News Analyser

A modern Django-based web application that monitors and analyzes financial news sentiment in real time, connects stories to user-selected stocks, and provides actionable summaries with market impact scoring.

## Main Features

- **Unified Search**: Users search by ticker or keyword to find relevant news across RSS feeds, APIs, and scrapers.
- **Watchlists**: Personalize with stocks of interest and view the latest news and sentiment for each.
- **Sentiment Scoring**: Articles are analyzed with NLP and assigned a market impact score between -1 (negative) and +1 (positive).
- **Aggregated Impact**: Each asset/ticker receives a rolling sentiment summary, reflecting recent news trends.
- **Search History**: Users can revisit previous searches for convenience and trend analysis.
- **Responsive UI**: Django templates enhanced with Alpine.js and HTMX for fast, modern, dynamic interactions with minimal JavaScript.
- **Scalable Architecture**: Docker, PostgreSQL, Celery, and Redis orchestrate background jobs, database reliability, and real-time data processing. (Do not implement redis caching.)

## How It Works

1. **Ingestion**: Collects news articles from specified RSS feeds, APIs, and web scrapers.
2. **Entity Extraction**: Recognizes stock tickers and relevant entities in the news text for accurate linkage. The scoring is done through the Gemini API.
3. **Sentiment Analysis**: Employs NLP to assess market impact and assign a sentiment score.The scoring is done through the Gemini API.
4. **User Access**: Delivers news, sentiment scores, and historical data through a clean, performance-optimized interface.
5. **Persistent History**: Saves user searches and assets for easy recall and analysis.

## Tech Stack

- **Backend**: Django (Python 3.x, SSR template rendering, admin, custom endpoints)
- **Database**: PostgreSQL (structured, relational data)
- **Background Processing**: Celery (distributed task queues) and Redis (message broker)
- **Containerization**: Docker Compose for local development and deployment
- **Frontend**: Minimal JavaScript via Alpine.js and HTMX for dynamic interaction on top of Django templates



---

Would you like this tailored as a GitHub README, a startup pitch, or a technical spec with integration details?
