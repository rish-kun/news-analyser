"""
Simplified Celery Tasks for News Scraping
Uses the refactored synchronous scraper
"""

from __future__ import absolute_import, unicode_literals
import logging
from celery import shared_task
from django.utils import timezone
from .scraper_refactored import NewsScraperRefactored

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_all_news_sources(self):
    """
    Master task to scrape all configured news sources
    Called by Celery Beat scheduler
    """
    try:
        logger.info("=" * 80)
        logger.info("Starting scheduled news scraping task")
        logger.info("=" * 80)

        # Initialize scraper
        scraper = NewsScraperRefactored(timeout=30, max_retries=3)

        # Scrape all feeds
        results = scraper.scrape_all_feeds()

        # Log results
        logger.info(f"Scraping Results:")
        logger.info(f"  Total Feeds: {results['total_feeds']}")
        logger.info(f"  Successful: {results['successful_feeds']}")
        logger.info(f"  Failed: {results['failed_feeds']}")
        logger.info(f"  Total Articles: {results['total_articles']}")

        # Save articles to database and trigger analysis
        total_saved = 0
        total_duplicates = 0

        for feed_result in results['feeds']:
            if feed_result['success'] and feed_result['articles']:
                # Save articles
                save_stats = scraper.save_articles_to_db(
                    articles=feed_result['articles'],
                    source_name=feed_result['feed_name']
                )

                total_saved += save_stats['saved']
                total_duplicates += save_stats['duplicates']

                # Trigger sentiment analysis for new articles
                if save_stats['saved'] > 0:
                    logger.info(f"Triggering sentiment analysis for {save_stats['saved']} new articles from {feed_result['feed_name']}")
                    analyze_recent_articles.delay(hours=1)

        logger.info(f"Database Save Summary:")
        logger.info(f"  New Articles Saved: {total_saved}")
        logger.info(f"  Duplicates Skipped: {total_duplicates}")
        logger.info("=" * 80)

        return {
            'status': 'success',
            'timestamp': timezone.now().isoformat(),
            'feeds_scraped': results['successful_feeds'],
            'articles_found': results['total_articles'],
            'articles_saved': total_saved,
            'duplicates': total_duplicates
        }

    except Exception as e:
        logger.error(f"Error in scrape_all_news_sources task: {e}", exc_info=True)
        # Retry the task
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def scrape_single_feed(self, feed_key: str):
    """
    Scrape a single news feed

    Args:
        feed_key: Key identifying the feed to scrape
    """
    try:
        logger.info(f"Scraping single feed: {feed_key}")

        scraper = NewsScraperRefactored(timeout=30, max_retries=3)
        result = scraper.scrape_feed(feed_key)

        if result['success']:
            # Save articles
            save_stats = scraper.save_articles_to_db(
                articles=result['articles'],
                source_name=result['feed_name']
            )

            logger.info(
                f"Feed '{result['feed_name']}' scraped: "
                f"{len(result['articles'])} found, {save_stats['saved']} saved"
            )

            # Trigger analysis if new articles were saved
            if save_stats['saved'] > 0:
                analyze_recent_articles.delay(hours=1)

            return {
                'status': 'success',
                'feed_key': feed_key,
                'feed_name': result['feed_name'],
                'articles_found': len(result['articles']),
                'articles_saved': save_stats['saved']
            }
        else:
            logger.error(f"Failed to scrape feed '{feed_key}': {result.get('error')}")
            return {
                'status': 'error',
                'feed_key': feed_key,
                'error': result.get('error')
            }

    except Exception as e:
        logger.error(f"Error in scrape_single_feed task for '{feed_key}': {e}", exc_info=True)
        raise self.retry(exc=e)


@shared_task
def analyze_recent_articles(hours: int = 24):
    """
    Analyze sentiment for recent unanalyzed articles

    Args:
        hours: Look for articles published within this many hours
    """
    from news_analyser.models import News
    from news_analyser.tasks import analyze_article_sentiment
    from datetime import timedelta

    try:
        logger.info(f"Finding unanalyzed articles from last {hours} hours")

        # Get unanalyzed articles from the last N hours
        cutoff_time = timezone.now() - timedelta(hours=hours)
        unanalyzed_articles = News.objects.filter(
            is_analyzed=False,
            date__gte=cutoff_time
        ).order_by('-date')[:50]  # Limit to 50 articles per batch

        count = unanalyzed_articles.count()
        logger.info(f"Found {count} unanalyzed articles")

        if count == 0:
            return {'status': 'success', 'articles_analyzed': 0}

        # Trigger sentiment analysis for each article
        for news in unanalyzed_articles:
            logger.info(f"Triggering analysis for article ID {news.id}: {news.title[:50]}...")
            analyze_article_sentiment.delay(news.id)

        return {
            'status': 'success',
            'articles_queued': count,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in analyze_recent_articles: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_unanalyzed_articles(days: int = 7):
    """
    Clean up old articles that were never analyzed

    Args:
        days: Remove unanalyzed articles older than this many days
    """
    from news_analyser.models import News
    from datetime import timedelta

    try:
        logger.info(f"Cleaning up unanalyzed articles older than {days} days")

        cutoff_date = timezone.now() - timedelta(days=days)
        old_articles = News.objects.filter(
            is_analyzed=False,
            date__lt=cutoff_date
        )

        count = old_articles.count()
        if count > 0:
            old_articles.delete()
            logger.info(f"Deleted {count} old unanalyzed articles")

        return {
            'status': 'success',
            'deleted_count': count,
            'timestamp': timezone.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in cleanup_old_unanalyzed_articles: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True)
def test_scraping_system(self):
    """
    Test task to verify the scraping system is working
    Scrapes one feed and logs the results
    """
    try:
        logger.info("=" * 80)
        logger.info("TESTING SCRAPING SYSTEM")
        logger.info("=" * 80)

        scraper = NewsScraperRefactored()

        # Test with Economic Times Markets feed
        test_feed = 'economic_times_markets'
        logger.info(f"Testing with feed: {test_feed}")

        result = scraper.scrape_feed(test_feed)

        if result['success']:
            logger.info(f"✓ Successfully scraped {len(result['articles'])} articles")

            if result['articles']:
                logger.info("Sample article:")
                sample = result['articles'][0]
                logger.info(f"  Title: {sample['title']}")
                logger.info(f"  Link: {sample['link']}")
                logger.info(f"  Published: {sample['published_at']}")

                # Try saving to database
                save_stats = scraper.save_articles_to_db(
                    articles=result['articles'][:5],  # Save first 5 as test
                    source_name=result['feed_name']
                )
                logger.info(f"✓ Database save test: {save_stats['saved']} saved, {save_stats['duplicates']} duplicates")

            logger.info("=" * 80)
            logger.info("SCRAPING SYSTEM TEST: PASSED ✓")
            logger.info("=" * 80)

            return {
                'status': 'success',
                'test': 'passed',
                'articles_found': len(result['articles'])
            }
        else:
            logger.error(f"✗ Scraping failed: {result.get('error')}")
            logger.info("=" * 80)
            logger.info("SCRAPING SYSTEM TEST: FAILED ✗")
            logger.info("=" * 80)

            return {
                'status': 'error',
                'test': 'failed',
                'error': result.get('error')
            }

    except Exception as e:
        logger.error(f"✗ Test exception: {e}", exc_info=True)
        logger.info("=" * 80)
        logger.info("SCRAPING SYSTEM TEST: ERROR ✗")
        logger.info("=" * 80)

        return {
            'status': 'error',
            'test': 'error',
            'error': str(e)
        }
