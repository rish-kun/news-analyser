# System Architecture & Implementation Overview

Visual guide to the News Analyser system architecture and key components.

## System Architecture Diagram

```
                                    ┌─────────────────────────────────┐
                                    │      External Data Sources       │
                                    │                                  │
                                    │  ┌────────────┐  ┌────────────┐│
                                    │  │ RSS Feeds  │  │   News     ││
                                    │  │ (ET, BS,   │  │  Websites  ││
                                    │  │  Mint)     │  │            ││
                                    │  └────────────┘  └────────────┘│
                                    └─────────────────────────────────┘
                                                  │
                                                  ▼
                              ┌───────────────────────────────────────┐
                              │      Celery Beat Scheduler            │
                              │  ┌─────────────────────────────────┐ │
                              │  │  Market Hours: Every 30 min     │ │
                              │  │  Off-Hours: Every 2 hours       │ │
                              │  │  Daily Summary: 5 PM IST        │ │
                              │  └─────────────────────────────────┘ │
                              └───────────────────────────────────────┘
                                                  │
                                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            CELERY WORKERS (Background Tasks)                  │
│                                                                               │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐       │
│  │  Scraping Tasks   │  │  Analysis Tasks   │  │ Aggregation Tasks │       │
│  │                   │  │                   │  │                   │       │
│  │ • scrape_all_     │  │ • analyze_        │  │ • aggregate_      │       │
│  │   sources()       │  │   article_        │  │   ticker_         │       │
│  │                   │  │   sentiment()     │  │   sentiment()     │       │
│  │ • scrape_rss_     │  │                   │  │                   │       │
│  │   source()        │  │ • analyze_        │  │ • aggregate_all_  │       │
│  │                   │  │   pending_        │  │   tickers()       │       │
│  └───────────────────┘  │   articles()      │  │                   │       │
│                         └───────────────────┘  └───────────────────┘       │
│                                                                               │
│  ┌───────────────────┐  ┌───────────────────┐                               │
│  │ Maintenance Tasks │  │  Reporting Tasks  │                               │
│  │                   │  │                   │                               │
│  │ • cleanup_old_    │  │ • generate_       │                               │
│  │   articles()      │  │   market_         │                               │
│  │                   │  │   summary()       │                               │
│  │ • cleanup_cache() │  │                   │                               │
│  └───────────────────┘  └───────────────────┘                               │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        SENTIMENT ANALYSIS ENGINE                              │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Multi-Model Ensemble Analysis                      │    │
│  │                                                                       │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐│    │
│  │  │   Gemini AI  │  │   FinBERT    │  │    VADER     │  │TextBlob ││    │
│  │  │   (40%)      │  │   (30%)      │  │    (20%)     │  │  (10%)  ││    │
│  │  │              │  │              │  │              │  │         ││    │
│  │  │ Contextual   │  │ Finance      │  │ Social       │  │Baseline ││    │
│  │  │ Analysis     │  │ Specific     │  │ Sentiment    │  │Polarity ││    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────┘│    │
│  │                                 │                                   │    │
│  │                                 ▼                                   │    │
│  │                    ┌─────────────────────────┐                     │    │
│  │                    │  Weighted Composite     │                     │    │
│  │                    │  Sentiment Score        │                     │    │
│  │                    │  + Confidence Metric    │                     │    │
│  │                    └─────────────────────────┘                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Ticker Recognition System                        │    │
│  │                                                                       │    │
│  │  • NSE India Ticker Database (500+ stocks)                          │    │
│  │  • Fuzzy Matching (85% threshold)                                   │    │
│  │  • Company Name Variations                                          │    │
│  │  • Multi-Ticker Detection                                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Sector Analysis Engine                           │    │
│  │                                                                       │    │
│  │  • 10 Major Sectors (Banking, IT, Pharma, etc.)                     │    │
│  │  • Sentiment Aggregation                                            │    │
│  │  • Rotation Signal Detection                                        │    │
│  │  • Trending Sector Identification                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            DATA STORAGE LAYER                                 │
│                                                                               │
│  ┌─────────────────────┐                    ┌─────────────────────┐         │
│  │   PostgreSQL DB     │                    │    Redis Cache      │         │
│  │                     │                    │                     │         │
│  │  ┌───────────────┐  │                    │ • Ticker Sentiment  │         │
│  │  │  News         │  │                    │   (5 min TTL)       │         │
│  │  │  • 10+ fields │  │                    │                     │         │
│  │  │  • Indexes    │  │                    │ • Sector Summary    │         │
│  │  └───────────────┘  │                    │   (15 min TTL)      │         │
│  │                     │                    │                     │         │
│  │  ┌───────────────┐  │                    │ • Market Summary    │         │
│  │  │SentimentScore │  │                    │   (1 hour TTL)      │         │
│  │  │  • Multi-model│  │                    │                     │         │
│  │  │  • Confidence │  │                    │ • Ticker Data       │         │
│  │  └───────────────┘  │                    │   (1 hour TTL)      │         │
│  │                     │                    └─────────────────────┘         │
│  │  ┌───────────────┐  │                                                    │
│  │  │  Stock        │  │                                                    │
│  │  │  • Symbol     │  │                                                    │
│  │  │  • Sector     │  │                                                    │
│  │  └───────────────┘  │                                                    │
│  │                     │                                                    │
│  │  ┌───────────────┐  │                                                    │
│  │  │  Sector       │  │                                                    │
│  │  │  • Keywords   │  │                                                    │
│  │  └───────────────┘  │                                                    │
│  └─────────────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION LAYER                                    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Django Application                             │    │
│  │                                                                       │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │    │
│  │  │  Web Views   │  │  REST API    │  │  Admin Panel │              │    │
│  │  │              │  │              │  │              │              │    │
│  │  │ • Templates  │  │ • ViewSets   │  │ • Model Mgmt │              │    │
│  │  │ • Forms      │  │ • Serializer │  │ • Bulk Edit  │              │    │
│  │  │ • HTMX       │  │ • Pagination │  │ • Filters    │              │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        REST API Endpoints                             │    │
│  │                                                                       │    │
│  │  • /api/news/                    - News CRUD + search                │    │
│  │  • /api/sentiment/ticker/{sym}/  - Ticker sentiment                 │    │
│  │  • /api/sentiment/sector/{name}/ - Sector sentiment                 │    │
│  │  • /api/sentiment/market_summary/- Market overview                  │    │
│  │  • /api/sentiment/trending/      - Trending sectors                 │    │
│  │  • /api/stocks/                  - Stock data + history             │    │
│  │  • /api/sectors/                 - Sector data                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Security & Performance                            │    │
│  │                                                                       │    │
│  │  • Rate Limiting: 100/hr anon, 1000/hr auth                         │    │
│  │  • CSRF Protection                                                   │    │
│  │  • CORS Configuration                                                │    │
│  │  • SQL Injection Prevention (ORM)                                   │    │
│  │  • XSS Protection                                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                              ┌───────────────────┐
                              │   End Users       │
                              │                   │
                              │ • Web Browser     │
                              │ • Mobile App      │
                              │ • API Clients     │
                              └───────────────────┘
```

## Data Flow Diagrams

### News Scraping & Analysis Flow

```
┌─────────────┐
│   Celery    │
│    Beat     │ (Every 30 min during market hours)
└─────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  scrape_all_sources()               │
│  - Coordinates all scraping         │
└─────────────────────────────────────┘
      │
      ├──────────────────────┬──────────────────────┐
      ▼                      ▼                      ▼
┌──────────────┐    ┌──────────────┐      ┌──────────────┐
│Economic Times│    │Business Std  │      │  LiveMint    │
│ RSS Scraper  │    │ RSS Scraper  │      │ RSS Scraper  │
└──────────────┘    └──────────────┘      └──────────────┘
      │                      │                      │
      └──────────────────────┴──────────────────────┘
                             ▼
                  ┌─────────────────────┐
                  │  Deduplication      │
                  │  - Content Hash     │
                  │  - URL Check        │
                  │  - SimHash          │
                  └─────────────────────┘
                             ▼
                  ┌─────────────────────┐
                  │  Save to Database   │
                  │  (News Model)       │
                  └─────────────────────┘
                             ▼
                  ┌─────────────────────┐
                  │ Queue Analysis Task │
                  │ (Celery)            │
                  └─────────────────────┘
                             ▼
            ┌─────────────────────────────────────┐
            │  analyze_article_sentiment()        │
            │                                     │
            │  1. Extract text                    │
            │  2. Recognize tickers               │
            │  3. Identify sectors                │
            │  4. Run 4 sentiment models          │
            │  5. Calculate composite score       │
            │  6. Extract entities                │
            └─────────────────────────────────────┘
                             ▼
                  ┌─────────────────────┐
                  │ Save SentimentScore │
                  │ - Per ticker        │
                  │ - Per sector        │
                  └─────────────────────┘
                             ▼
                  ┌─────────────────────┐
                  │  Update Cache       │
                  │  - Invalidate old   │
                  │  - Trigger aggreg.  │
                  └─────────────────────┘
```

### API Request Flow

```
┌──────────────┐
│   Client     │
│  Request     │
└──────────────┘
      │
      ▼
┌──────────────────────────────┐
│  Django Middleware           │
│  - CORS                      │
│  - Authentication            │
│  - Rate Limiting             │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│  URL Router                  │
│  /api/sentiment/ticker/X/    │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│  ViewSet                     │
│  SentimentViewSet            │
│  .ticker_sentiment()         │
└──────────────────────────────┘
      │
      ├─────────────► Check Cache ────────┐
      │                   │                │
      │                   │ Cache Hit      │
      │                   ▼                │
      │            Return Cached ◄─────────┘
      │
      │ Cache Miss
      ▼
┌──────────────────────────────┐
│  Trigger Celery Task         │
│  aggregate_ticker_sentiment()│
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│  Query Database              │
│  - Get recent scores         │
│  - Calculate averages        │
│  - Apply time weights        │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│  Store in Cache              │
│  TTL: 5 minutes              │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│  Serialize Response          │
│  TickerSentimentSerializer   │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│  Return JSON Response        │
│  + Rate Limit Headers        │
└──────────────────────────────┘
      │
      ▼
┌──────────────┐
│   Client     │
│  Response    │
└──────────────┘
```

## Database Schema

```
┌─────────────────────────────────┐
│           News                  │
├─────────────────────────────────┤
│ PK  id                          │
│     title (varchar 500)         │
│     content_summary (text)      │
│     content (text)              │
│     link (varchar 500) UNIQUE   │
│     author (varchar 200)        │
│     image_url (url)             │
│     tags (JSON)                 │
│     published_at (datetime)     │
│     scraped_at (datetime)       │
│     updated_at (datetime)       │
│     is_analyzed (boolean)       │
│     content_hash (varchar 64)   │
│     impact_rating (float)       │
│ FK  source_id                   │
│ FK  keyword_id                  │
│ M2M tickers                     │
│ M2M sectors                     │
└─────────────────────────────────┘
         │
         │ (1:N)
         ▼
┌─────────────────────────────────┐
│      SentimentScore             │
├─────────────────────────────────┤
│ PK  id                          │
│ FK  news_id                     │
│ FK  ticker_id (nullable)        │
│ FK  sector_id (nullable)        │
│     gemini_score (float)        │
│     finbert_score (float)       │
│     vader_score (float)         │
│     textblob_score (float)      │
│     sentiment_score (float)     │
│     sentiment_label (varchar)   │
│     confidence (float)          │
│     entities (JSON)             │
│     keywords_extracted (JSON)   │
│     analysis_details (JSON)     │
│     created_at (datetime)       │
│     model_used (varchar)        │
└─────────────────────────────────┘
         │
         │ (N:1)
         ▼
┌─────────────────────────────────┐
│           Stock                 │
├─────────────────────────────────┤
│ PK  id                          │
│     name (varchar 200)          │
│     symbol (varchar 20)         │
│ FK  sector_id                   │
│ M2M keywords                    │
└─────────────────────────────────┘
         │
         │ (N:1)
         ▼
┌─────────────────────────────────┐
│          Sector                 │
├─────────────────────────────────┤
│ PK  id                          │
│     name (varchar 200)          │
│     search_fields (varchar)     │
└─────────────────────────────────┘
```

## Module Structure

```
news_analyser/
│
├── sentiment/
│   ├── __init__.py
│   ├── analyzer.py           # AdvancedSentimentAnalyzer
│   │   ├── Class: AdvancedSentimentAnalyzer
│   │   ├── Methods:
│   │   │   ├── analyze_sentiment() - Main entry point
│   │   │   ├── _analyze_with_gemini() - Gemini API call
│   │   │   ├── _analyze_with_finbert() - FinBERT inference
│   │   │   ├── _analyze_with_vader() - VADER scoring
│   │   │   ├── _analyze_with_textblob() - TextBlob analysis
│   │   │   ├── _calculate_composite_score() - Ensemble
│   │   │   └── _calculate_confidence() - Confidence metric
│   │
│   ├── sector_analyzer.py    # SectorSentimentAnalyzer
│   │   ├── Class: SectorSentimentAnalyzer
│   │   ├── Methods:
│   │   │   ├── identify_sectors() - Sector detection
│   │   │   ├── get_sector_sentiment() - Aggregate sentiment
│   │   │   ├── get_trending_sectors() - Trending calculation
│   │   │   ├── get_sector_rotation_signals() - Rotation detection
│   │   │   └── get_sector_correlation() - Cross-sector analysis
│   │
│   └── utils.py              # Utility functions
│       ├── Class: TickerRecognizer
│       ├── Methods:
│       │   ├── find_tickers_in_text() - Ticker extraction
│       │   ├── _add_company_variations() - Name variants
│       │   └── _similarity() - Fuzzy matching
│       └── Functions:
│           ├── extract_entities() - NER extraction
│           └── calculate_confidence() - Confidence calc
│
├── scraping/
│   ├── __init__.py
│   ├── base_scraper.py       # Abstract base
│   │   └── Class: BaseScraper (ABC)
│   │
│   ├── rss_scraper.py        # RSS implementation
│   │   ├── Class: RSSFeedScraper
│   │   └── Class: IndianNewsRSSConfig
│   │
│   ├── web_scraper.py        # BeautifulSoup
│   │   └── Class: WebScraper
│   │
│   ├── selenium_scraper.py   # Selenium
│   │   └── Class: SeleniumScraper
│   │
│   └── deduplication.py      # Dedup logic
│       └── Class: ContentDeduplicator
│
└── api/
    ├── __init__.py
    ├── serializers.py        # DRF serializers
    │   ├── NewsListSerializer
    │   ├── NewsDetailSerializer
    │   ├── SentimentScoreSerializer
    │   ├── TickerSentimentSerializer
    │   └── MarketSummarySerializer
    │
    ├── views.py              # ViewSets
    │   ├── NewsViewSet
    │   ├── SentimentViewSet
    │   ├── StockViewSet
    │   └── SectorViewSet
    │
    └── urls.py               # URL routing
```

## Key Performance Features

### Caching Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    Redis Cache                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ticker_sentiment_{SYMBOL}_{HOURS}h                    │
│  ├── TTL: 5 minutes                                    │
│  └── Contains: avg, weighted_avg, count, timestamp     │
│                                                         │
│  sector_sentiment_{SECTOR}_{HOURS}h                    │
│  ├── TTL: 15 minutes                                   │
│  └── Contains: avg, distribution, article_count        │
│                                                         │
│  daily_market_summary                                  │
│  ├── TTL: 1 hour                                       │
│  └── Contains: market_sentiment, sectors, trends       │
│                                                         │
│  ticker_data_cache                                     │
│  ├── TTL: 1 hour                                       │
│  └── Contains: ticker_data, company_variations         │
│                                                         │
│  content_hash_{HASH}                                   │
│  ├── TTL: 24 hours                                     │
│  └── Purpose: Deduplication tracking                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Database Indexes

```sql
-- News table indexes
CREATE INDEX idx_news_published_source
  ON news_article(published_at DESC, source_id);

CREATE INDEX idx_news_analyzed
  ON news_article(is_analyzed)
  WHERE is_analyzed = FALSE;

CREATE INDEX idx_news_scraped
  ON news_article(scraped_at DESC);

CREATE INDEX idx_news_content_hash
  ON news_article(content_hash);

-- SentimentScore indexes
CREATE INDEX idx_sentiment_ticker_time
  ON sentiment_score(ticker_id, created_at DESC);

CREATE INDEX idx_sentiment_sector_time
  ON sentiment_score(sector_id, created_at DESC);

CREATE INDEX idx_sentiment_score_range
  ON sentiment_score(sentiment_score)
  WHERE sentiment_score > 0.5 OR sentiment_score < -0.5;

CREATE INDEX idx_sentiment_created
  ON sentiment_score(created_at DESC);

-- Full-text search
CREATE INDEX idx_news_search
  ON news_article
  USING gin(to_tsvector('english', title || ' ' || content));
```

---

**This architecture supports:**
- 100+ articles/minute scraping
- 60+ articles/minute sentiment analysis
- 1000+ API requests/minute
- <500ms API response time (p95)
- >80% cache hit rate
- >90% ticker recognition accuracy
