"""
Celery tasks for news scraping and sentiment analysis
"""

from __future__ import absolute_import, unicode_literals
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from celery import shared_task, group, chord
from django.utils import timezone
from django.db.models import Avg, Count
from django.core.cache import cache
from google import genai
from blackbox.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)


# ============================================================================
# SCRAPING TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_all_sources(self):
    """
    Master task to coordinate scraping from all news sources
    Runs every 30 minutes during market hours, every 2 hours during off-hours
    """
    from .models import Source
    from .scraping.rss_scraper import IndianNewsRSSConfig

    try:
        logger.info("Starting scrape_all_sources task")

        # Get all active sources
        active_sources = Source.objects.filter(is_active=True)

        # Create scraping tasks for each source
        tasks = []

        # RSS sources
        for source_key in IndianNewsRSSConfig.FEEDS.keys():
            tasks.append(scrape_rss_source.s(source_key))

        # Execute scraping tasks in parallel
        job = group(tasks)
        result = job.apply_async()

        logger.info(f"Dispatched {len(tasks)} scraping tasks")

        return {"status": "success", "tasks_dispatched": len(tasks)}

    except Exception as e:
        logger.error(f"Error in scrape_all_sources: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def scrape_rss_source(self, source_key: str):
    """
    Scrape a specific RSS news source

    Args:
        source_key: Key identifying the news source
    """
    from .models import News, Source, Keyword
    from .scraping.rss_scraper import IndianNewsRSSConfig
    from .scraping.deduplication import ContentDeduplicator

    try:
        logger.info(f"Scraping RSS source: {source_key}")

        # Get scraper
        scraper = IndianNewsRSSConfig.get_scraper(source_key)
        if not scraper:
            logger.error(f"Unknown source key: {source_key}")
            return {"status": "error", "message": "Unknown source"}

        # Scrape articles
        articles = asyncio.run(scraper.scrape())

        logger.info(f"Scraped {len(articles)} articles from {source_key}")

        # Deduplicate
        deduplicator = ContentDeduplicator()
        unique_articles = deduplicator.deduplicate_articles(articles)

        logger.info(f"After deduplication: {len(unique_articles)} unique articles")

        # Get or create source
        source, _ = Source.objects.get_or_create(
            id_name=source_key,
            defaults={
                'name': scraper.source_name,
                'url': scraper.source_url,
                'is_active': True
            }
        )

        # Update last scraped time
        source.last_scraped = timezone.now()
        source.save()

        # Save articles to database
        saved_count = 0
        for article in unique_articles:
            try:
                # Create or get default keyword
                keyword, _ = Keyword.objects.get_or_create(name="general")

                # Create news object
                news, created = News.objects.get_or_create(
                    link=article['link'],
                    defaults={
                        'title': article['title'],
                        'content_summary': article['content_summary'],
                        'content': article.get('content', ''),
                        'author': article.get('author', ''),
                        'image_url': article.get('image_url', ''),
                        'published_at': article.get('published_at'),
                        'content_hash': article.get('content_hash'),
                        'source': source,
                        'keyword': keyword,
                        'is_analyzed': False
                    }
                )

                if created:
                    saved_count += 1

                    # Trigger sentiment analysis
                    analyze_article_sentiment.delay(news.id)

            except Exception as e:
                logger.error(f"Error saving article: {e}")
                continue

        logger.info(f"Saved {saved_count} new articles from {source_key}")

        return {
            "status": "success",
            "source": source_key,
            "scraped": len(articles),
            "unique": len(unique_articles),
            "saved": saved_count
        }

    except Exception as e:
        logger.error(f"Error scraping {source_key}: {e}")
        raise self.retry(exc=e)


# ============================================================================
# SENTIMENT ANALYSIS TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def analyze_article_sentiment(self, news_id: int):
    """
    Analyze sentiment for a single news article

    Args:
        news_id: ID of the news article
    """
    from .models import News, SentimentScore, Stock, Sector
    from .sentiment.analyzer import AdvancedSentimentAnalyzer
    from .sentiment.utils import TickerRecognizer, extract_entities
    from .sentiment.sector_analyzer import SectorSentimentAnalyzer

    try:
        logger.info(f"Analyzing sentiment for news ID: {news_id}")

        # Get news article
        news = News.objects.get(id=news_id)

        # Initialize analyzers
        sentiment_analyzer = AdvancedSentimentAnalyzer()
        ticker_recognizer = TickerRecognizer()
        sector_analyzer = SectorSentimentAnalyzer()

        # Perform sentiment analysis
        sentiment_result = asyncio.run(
            sentiment_analyzer.analyze_sentiment(
                text=news.content or news.content_summary,
                title=news.title
            )
        )

        # Update news impact rating (for backward compatibility)
        news.impact_rating = sentiment_result['composite_score']

        # Find mentioned tickers
        full_text = f"{news.title} {news.content_summary} {news.content or ''}"
        mentioned_tickers = ticker_recognizer.find_tickers_in_text(full_text)

        logger.info(f"Found {len(mentioned_tickers)} ticker mentions")

        # Find mentioned sectors
        mentioned_sectors = sector_analyzer.identify_sectors(full_text)

        logger.info(f"Identified sectors: {mentioned_sectors}")

        # Extract entities
        entities = extract_entities(full_text)

        # Save sentiment scores for each ticker
        for ticker_info in mentioned_tickers:
            try:
                stock = Stock.objects.filter(symbol=ticker_info['symbol']).first()

                if stock:
                    # Add to news tickers
                    news.tickers.add(stock)

                    # Create sentiment score
                    sentiment_label = AdvancedSentimentAnalyzer.get_sentiment_label(
                        sentiment_result['composite_score']
                    )

                    SentimentScore.objects.update_or_create(
                        news=news,
                        ticker=stock,
                        defaults={
                            'gemini_score': sentiment_result.get('gemini_score'),
                            'finbert_score': sentiment_result.get('finbert_score'),
                            'vader_score': sentiment_result.get('vader_score'),
                            'textblob_score': sentiment_result.get('textblob_score'),
                            'sentiment_score': sentiment_result['composite_score'],
                            'sentiment_label': sentiment_label,
                            'confidence': sentiment_result['confidence'],
                            'analysis_details': sentiment_result.get('analysis_details', {}),
                            'entities': entities,
                            'model_used': sentiment_result.get('model_used', 'ensemble')
                        }
                    )

            except Exception as e:
                logger.error(f"Error saving sentiment for ticker {ticker_info['symbol']}: {e}")

        # Save sentiment scores for each sector
        for sector_name in mentioned_sectors:
            try:
                sector = Sector.objects.filter(name__iexact=sector_name).first()

                if sector:
                    # Add to news sectors
                    news.sectors.add(sector)

                    # Create sentiment score
                    sentiment_label = AdvancedSentimentAnalyzer.get_sentiment_label(
                        sentiment_result['composite_score']
                    )

                    SentimentScore.objects.update_or_create(
                        news=news,
                        sector=sector,
                        defaults={
                            'gemini_score': sentiment_result.get('gemini_score'),
                            'finbert_score': sentiment_result.get('finbert_score'),
                            'vader_score': sentiment_result.get('vader_score'),
                            'textblob_score': sentiment_result.get('textblob_score'),
                            'sentiment_score': sentiment_result['composite_score'],
                            'sentiment_label': sentiment_label,
                            'confidence': sentiment_result['confidence'],
                            'analysis_details': sentiment_result.get('analysis_details', {}),
                            'entities': entities,
                            'model_used': sentiment_result.get('model_used', 'ensemble')
                        }
                    )

            except Exception as e:
                logger.error(f"Error saving sentiment for sector {sector_name}: {e}")

        # Mark as analyzed
        news.is_analyzed = True
        news.save()

        logger.info(f"Sentiment analysis completed for news ID: {news_id}")

        return {
            "status": "success",
            "news_id": news_id,
            "sentiment_score": sentiment_result['composite_score'],
            "tickers_found": len(mentioned_tickers),
            "sectors_found": len(mentioned_sectors)
        }

    except News.DoesNotExist:
        logger.error(f"News item {news_id} not found")
        return {"status": "error", "message": "News not found"}

    except Exception as e:
        logger.error(f"Error analyzing sentiment for news {news_id}: {e}")
        raise self.retry(exc=e)


@shared_task
def analyze_pending_articles(limit: int = 50):
    """
    Analyze sentiment for pending articles

    Args:
        limit: Maximum number of articles to analyze
    """
    from .models import News

    pending_articles = News.objects.filter(is_analyzed=False).order_by('-scraped_at')[:limit]

    logger.info(f"Found {pending_articles.count()} pending articles for analysis")

    # Create analysis tasks
    tasks = [analyze_article_sentiment.s(article.id) for article in pending_articles]

    # Execute in parallel
    job = group(tasks)
    job.apply_async()

    return {"status": "success", "articles_queued": len(tasks)}


# ============================================================================
# AGGREGATION TASKS
# ============================================================================

@shared_task
def aggregate_ticker_sentiment(ticker_symbol: str, hours: int = 24):
    """
    Calculate aggregated sentiment for a ticker over time windows

    Args:
        ticker_symbol: Stock ticker symbol
        hours: Time window in hours
    """
    from .models import Stock, SentimentScore

    try:
        stock = Stock.objects.filter(symbol=ticker_symbol).first()

        if not stock:
            logger.warning(f"Stock {ticker_symbol} not found")
            return {"status": "error", "message": "Stock not found"}

        # Calculate time windows
        now = timezone.now()
        cutoff_time = now - timedelta(hours=hours)

        # Get recent sentiment scores
        scores = SentimentScore.objects.filter(
            ticker=stock,
            created_at__gte=cutoff_time
        )

        if not scores.exists():
            return {"status": "success", "message": "No sentiment data", "ticker": ticker_symbol}

        # Calculate statistics
        stats = scores.aggregate(
            avg_sentiment=Avg('sentiment_score'),
            count=Count('id')
        )

        # Calculate weighted average (recent scores weighted more)
        weighted_scores = []
        total_weight = 0

        for score in scores:
            # Calculate age in hours
            age_hours = (now - score.created_at).total_seconds() / 3600

            # Weight decreases with age (exponential decay)
            weight = 2 ** (-age_hours / (hours / 2))

            weighted_scores.append(score.sentiment_score * weight)
            total_weight += weight

        weighted_avg = sum(weighted_scores) / total_weight if total_weight > 0 else 0

        # Cache results
        cache_key = f'ticker_sentiment_{ticker_symbol}_{hours}h'
        cache_data = {
            'ticker': ticker_symbol,
            'average_sentiment': stats['avg_sentiment'],
            'weighted_sentiment': weighted_avg,
            'article_count': stats['count'],
            'time_window_hours': hours,
            'timestamp': now.isoformat()
        }

        cache.set(cache_key, cache_data, 300)  # Cache for 5 minutes

        logger.info(f"Aggregated sentiment for {ticker_symbol}: {stats['avg_sentiment']}")

        return {"status": "success", **cache_data}

    except Exception as e:
        logger.error(f"Error aggregating sentiment for {ticker_symbol}: {e}")
        return {"status": "error", "message": str(e)}


@shared_task
def aggregate_all_tickers_sentiment():
    """
    Aggregate sentiment for all stocks with recent news
    """
    from .models import Stock, SentimentScore

    # Get stocks with sentiment scores in last 24 hours
    cutoff_time = timezone.now() - timedelta(hours=24)

    stocks_with_news = Stock.objects.filter(
        sentiment_scores__created_at__gte=cutoff_time
    ).distinct()

    logger.info(f"Aggregating sentiment for {stocks_with_news.count()} stocks")

    # Create aggregation tasks
    tasks = [aggregate_ticker_sentiment.s(stock.symbol) for stock in stocks_with_news]

    # Execute in parallel
    job = group(tasks)
    job.apply_async()

    return {"status": "success", "stocks_processed": stocks_with_news.count()}


# ============================================================================
# MAINTENANCE TASKS
# ============================================================================

@shared_task
def cleanup_old_articles(days: int = 30):
    """
    Archive or delete articles older than specified days

    Args:
        days: Age threshold in days
    """
    from .models import News

    cutoff_date = timezone.now() - timedelta(days=days)

    # Get old articles
    old_articles = News.objects.filter(published_at__lt=cutoff_date)

    count = old_articles.count()

    logger.info(f"Found {count} articles older than {days} days")

    # For now, just mark them (don't delete sentiment scores)
    # In production, you might want to move to cold storage

    # Delete articles without sentiment analysis
    articles_to_delete = old_articles.filter(is_analyzed=False)
    deleted_count = articles_to_delete.count()
    articles_to_delete.delete()

    logger.info(f"Deleted {deleted_count} old unanalyzed articles")

    return {
        "status": "success",
        "old_articles": count,
        "deleted": deleted_count
    }


@shared_task
def cleanup_cache():
    """
    Clear expired cache entries
    """
    try:
        cache.clear()
        logger.info("Cache cleared successfully")
        return {"status": "success", "message": "Cache cleared"}

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# REPORTING TASKS
# ============================================================================

@shared_task
def generate_market_summary():
    """
    Generate daily market sentiment summary
    """
    from .models import SentimentScore, Sector
    from .sentiment.sector_analyzer import SectorSentimentAnalyzer

    try:
        logger.info("Generating market summary")

        sector_analyzer = SectorSentimentAnalyzer()

        # Get sector sentiments
        sector_sentiments = sector_analyzer.get_all_sectors_sentiment(hours=24)

        # Get trending sectors
        trending_sectors = sector_analyzer.get_trending_sectors(hours=24, limit=5)

        # Get rotation signals
        rotation_signals = sector_analyzer.get_sector_rotation_signals(hours=24)

        # Calculate market-wide sentiment
        all_scores = SentimentScore.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        )

        market_stats = all_scores.aggregate(
            avg_sentiment=Avg('sentiment_score'),
            count=Count('id')
        )

        summary = {
            'date': timezone.now().date().isoformat(),
            'market_sentiment': market_stats['avg_sentiment'],
            'total_articles': market_stats['count'],
            'sector_sentiments': sector_sentiments,
            'trending_sectors': trending_sectors,
            'rotation_signals': rotation_signals,
            'generated_at': timezone.now().isoformat()
        }

        # Cache summary
        cache.set('daily_market_summary', summary, 3600)  # Cache for 1 hour

        logger.info("Market summary generated successfully")

        return {"status": "success", "summary": summary}

    except Exception as e:
        logger.error(f"Error generating market summary: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

@shared_task
def analyse_news_task(news_id):
    """
    Legacy task for backward compatibility
    Redirects to new analyze_article_sentiment task
    """
    return analyze_article_sentiment.delay(news_id)
