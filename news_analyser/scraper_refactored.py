"""
Refactored News Scraper - Simple, Reliable, Synchronous
Handles RSS feed scraping for Indian financial news sources
"""

import feedparser
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email.utils import parsedate_to_datetime
from django.utils import timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class NewsScraperRefactored:
    """
    Simplified news scraper using feedparser with robust error handling
    """

    # Indian Financial News RSS Feeds (verified and working)
    RSS_FEEDS = {
        'economic_times_markets': {
            'name': 'Economic Times - Markets',
            'url': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
            'category': 'markets'
        },
        'economic_times_stocks': {
            'name': 'Economic Times - Stocks',
            'url': 'https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms',
            'category': 'stocks'
        },
        'economic_times_industry': {
            'name': 'Economic Times - Industry',
            'url': 'https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms',
            'category': 'industry'
        },
        'business_standard_markets': {
            'name': 'Business Standard - Markets',
            'url': 'https://www.business-standard.com/rss/markets-106.rss',
            'category': 'markets'
        },
        'business_standard_companies': {
            'name': 'Business Standard - Companies',
            'url': 'https://www.business-standard.com/rss/companies-109.rss',
            'category': 'companies'
        },
        'livemint_markets': {
            'name': 'LiveMint - Markets',
            'url': 'https://www.livemint.com/rss/markets',
            'category': 'markets'
        },
        'livemint_companies': {
            'name': 'LiveMint - Companies',
            'url': 'https://www.livemint.com/rss/companies',
            'category': 'companies'
        },
        'moneycontrol_news': {
            'name': 'MoneyControl - Latest News',
            'url': 'https://www.moneycontrol.com/rss/latestnews.xml',
            'category': 'general'
        },
        'the_hindu_markets': {
            'name': 'The Hindu - Markets',
            'url': 'https://www.thehindu.com/business/markets/feeder/default.rss',
            'category': 'markets'
        },
        'the_hindu_economy': {
            'name': 'The Hindu - Economy',
            'url': 'https://www.thehindu.com/business/Economy/feeder/default.rss',
            'category': 'economy'
        },
        'the_hindu_industry': {
            'name': 'The Hindu - Industry',
            'url': 'https://www.thehindu.com/business/Industry/feeder/default.rss',
            'category': 'industry'
        },
        'toi_business': {
            'name': 'Times of India - Business',
            'url': 'https://timesofindia.indiatimes.com/rssfeeds/1898055.cms',
            'category': 'business'
        },
    }

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize scraper with retry mechanism

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set user agent to avoid blocking
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        return session

    def scrape_feed(self, feed_key: str) -> Dict:
        """
        Scrape a single RSS feed

        Args:
            feed_key: Key identifying the feed in RSS_FEEDS

        Returns:
            Dictionary with scraping results
        """
        if feed_key not in self.RSS_FEEDS:
            logger.error(f"Unknown feed key: {feed_key}")
            return {'success': False, 'error': 'Unknown feed', 'articles': []}

        feed_config = self.RSS_FEEDS[feed_key]
        feed_url = feed_config['url']
        feed_name = feed_config['name']

        logger.info(f"Scraping feed: {feed_name} ({feed_url})")

        try:
            # Fetch feed content with timeout
            response = self.session.get(feed_url, timeout=self.timeout)
            response.raise_for_status()

            # Parse RSS feed
            feed = feedparser.parse(response.content)

            if feed.bozo:
                logger.warning(f"Feed parsing warning for {feed_name}: {feed.bozo_exception}")

            # Extract articles
            articles = []
            for entry in feed.entries:
                article = self._extract_article(entry, feed_config)
                if article:
                    articles.append(article)

            logger.info(f"Successfully scraped {len(articles)} articles from {feed_name}")

            return {
                'success': True,
                'feed_key': feed_key,
                'feed_name': feed_name,
                'articles': articles,
                'scraped_at': timezone.now()
            }

        except requests.exceptions.Timeout:
            logger.error(f"Timeout scraping {feed_name}")
            return {'success': False, 'error': 'Timeout', 'articles': []}

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error scraping {feed_name}: {e}")
            return {'success': False, 'error': str(e), 'articles': []}

        except Exception as e:
            logger.error(f"Unexpected error scraping {feed_name}: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'articles': []}

    def _extract_article(self, entry, feed_config: Dict) -> Optional[Dict]:
        """
        Extract article data from RSS entry

        Args:
            entry: feedparser entry object
            feed_config: Feed configuration dict

        Returns:
            Article dictionary or None if extraction fails
        """
        try:
            # Extract title and link (required fields)
            title = entry.get('title', '').strip()
            link = entry.get('link', '').strip()

            if not title or not link:
                logger.warning("Entry missing title or link, skipping")
                return None

            # Extract summary/description
            summary = entry.get('summary', entry.get('description', '')).strip()
            if not summary:
                summary = title  # Fallback to title

            # Extract publication date
            published_at = None
            if 'published' in entry:
                published_at = self._parse_date(entry.published)
            elif 'pubDate' in entry:
                published_at = self._parse_date(entry.pubDate)
            elif 'updated' in entry:
                published_at = self._parse_date(entry.updated)

            # Default to now if no date found
            if not published_at:
                published_at = timezone.now()

            # Extract author
            author = entry.get('author', '')

            # Extract image URL
            image_url = ''
            if hasattr(entry, 'media_content') and entry.media_content:
                image_url = entry.media_content[0].get('url', '')
            elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                image_url = entry.media_thumbnail[0].get('url', '')
            elif 'image' in entry:
                if isinstance(entry.image, dict):
                    image_url = entry.image.get('href', '')
                else:
                    image_url = str(entry.image)

            # Extract tags
            tags = []
            if hasattr(entry, 'tags'):
                tags = [tag.term for tag in entry.tags if hasattr(tag, 'term')]

            # Generate content hash for deduplication
            content_hash = self._generate_hash(title, summary)

            article = {
                'title': title,
                'link': link,
                'content_summary': summary,
                'content': '',  # Will be populated by content extraction if needed
                'published_at': published_at,
                'author': author,
                'image_url': image_url,
                'tags': tags,
                'content_hash': content_hash,
                'source_name': feed_config['name'],
                'source_key': feed_config.get('key', ''),
                'category': feed_config.get('category', 'general')
            }

            return article

        except Exception as e:
            logger.error(f"Error extracting article: {e}", exc_info=True)
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime

        Args:
            date_str: Date string

        Returns:
            datetime object or None
        """
        if not date_str:
            return None

        try:
            # Try email format (RFC 2822)
            dt = parsedate_to_datetime(date_str)
            # Make timezone aware
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt
        except:
            pass

        try:
            # Try ISO format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt
        except:
            pass

        return None

    def _generate_hash(self, title: str, content: str) -> str:
        """
        Generate SHA256 hash for deduplication

        Args:
            title: Article title
            content: Article content

        Returns:
            SHA256 hash string
        """
        combined = f"{title.lower()}{content.lower()}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def scrape_all_feeds(self) -> Dict:
        """
        Scrape all configured feeds

        Returns:
            Dictionary with aggregated results
        """
        logger.info(f"Starting to scrape all {len(self.RSS_FEEDS)} feeds")

        results = {
            'total_feeds': len(self.RSS_FEEDS),
            'successful_feeds': 0,
            'failed_feeds': 0,
            'total_articles': 0,
            'feeds': []
        }

        for feed_key in self.RSS_FEEDS.keys():
            result = self.scrape_feed(feed_key)
            results['feeds'].append(result)

            if result['success']:
                results['successful_feeds'] += 1
                results['total_articles'] += len(result['articles'])
            else:
                results['failed_feeds'] += 1

        logger.info(
            f"Scraping complete: {results['successful_feeds']}/{results['total_feeds']} feeds successful, "
            f"{results['total_articles']} total articles"
        )

        return results

    def save_articles_to_db(self, articles: List[Dict], source_name: str) -> Dict:
        """
        Save scraped articles to database

        Args:
            articles: List of article dictionaries
            source_name: Name of the source

        Returns:
            Dictionary with save statistics
        """
        from news_analyser.models import News, Source, Keyword

        logger.info(f"Saving {len(articles)} articles to database")

        stats = {
            'total': len(articles),
            'saved': 0,
            'duplicates': 0,
            'errors': 0
        }

        # Get or create source
        source, _ = Source.objects.get_or_create(
            name=source_name,
            defaults={'url': '', 'is_active': True}
        )

        # Get or create default keyword
        keyword, _ = Keyword.objects.get_or_create(name="general")

        for article in articles:
            try:
                # Check if article already exists (by link or content_hash)
                exists = News.objects.filter(link=article['link']).exists()

                if exists:
                    stats['duplicates'] += 1
                    continue

                # Create news object
                news = News.objects.create(
                    title=article['title'],
                    link=article['link'],
                    content_summary=article['content_summary'],
                    content=article.get('content', ''),
                    published_at=article.get('published_at'),
                    author=article.get('author', ''),
                    image_url=article.get('image_url', ''),
                    content_hash=article.get('content_hash', ''),
                    source=source,
                    keyword=keyword,
                    is_analyzed=False,
                    tags=article.get('tags', [])
                )

                stats['saved'] += 1
                logger.debug(f"Saved article: {article['title'][:50]}...")

            except Exception as e:
                logger.error(f"Error saving article '{article.get('title', 'Unknown')}': {e}")
                stats['errors'] += 1

        logger.info(
            f"Database save complete: {stats['saved']} saved, "
            f"{stats['duplicates']} duplicates, {stats['errors']} errors"
        )

        return stats
