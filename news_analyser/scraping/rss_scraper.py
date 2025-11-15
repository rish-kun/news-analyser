"""
RSS Feed scraper with async support
"""

import asyncio
import logging
from typing import List, Dict, Optional
import feedparser
import aiohttp
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class RSSFeedScraper(BaseScraper):
    """
    Scraper for RSS/Atom feeds with async support
    """

    def __init__(self, source_name: str, feed_urls: List[str], timeout: int = 30):
        """
        Initialize RSS feed scraper

        Args:
            source_name: Name of the news source
            feed_urls: List of RSS feed URLs to scrape
            timeout: Request timeout in seconds
        """
        super().__init__(source_name, feed_urls[0] if feed_urls else "")
        self.feed_urls = feed_urls
        self.timeout = timeout

    async def scrape(self) -> List[Dict]:
        """
        Scrape all configured RSS feeds

        Returns:
            List of article dictionaries
        """
        all_articles = []

        # Scrape all feeds concurrently
        tasks = [self._scrape_feed(url) for url in self.feed_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                self.logger.error(f"Feed scraping error: {result}")

        # Remove duplicates based on link
        unique_articles = {}
        for article in all_articles:
            if self.validate_article(article):
                link = article['link']
                if link not in unique_articles:
                    unique_articles[link] = self.normalize_article(article)

        return list(unique_articles.values())

    async def _scrape_feed(self, feed_url: str) -> List[Dict]:
        """
        Scrape a single RSS feed

        Args:
            feed_url: URL of the RSS feed

        Returns:
            List of articles from the feed
        """
        try:
            # Fetch feed content
            async with aiohttp.ClientSession() as session:
                async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to fetch {feed_url}: HTTP {response.status}")
                        return []

                    content = await response.text()

            # Parse RSS feed
            feed = await asyncio.to_thread(feedparser.parse, content)

            if feed.bozo:
                self.logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")

            articles = []

            for entry in feed.entries:
                article = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', entry.get('description', '')),
                    'published': entry.get('published', entry.get('pubDate', '')),
                    'author': entry.get('author', ''),
                }

                # Extract image URL if available
                if hasattr(entry, 'media_content'):
                    article['image_url'] = entry.media_content[0].get('url', '') if entry.media_content else ''
                elif hasattr(entry, 'media_thumbnail'):
                    article['image_url'] = entry.media_thumbnail[0].get('url', '') if entry.media_thumbnail else ''

                # Extract tags
                if hasattr(entry, 'tags'):
                    article['tags'] = [tag.term for tag in entry.tags]

                articles.append(article)

            self.logger.info(f"Scraped {len(articles)} articles from {feed_url}")
            return articles

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout while fetching {feed_url}")
            return []
        except Exception as e:
            self.logger.error(f"Error scraping RSS feed {feed_url}: {e}")
            return []

    async def scrape_article_content(self, url: str) -> Optional[Dict]:
        """
        Scrape full article content from URL

        Args:
            url: Article URL

        Returns:
            Dictionary with article content
        """
        try:
            from newspaper import Article

            # Use newspaper3k for content extraction
            article = Article(url)

            await asyncio.to_thread(article.download)
            await asyncio.to_thread(article.parse)

            content_data = {
                'title': article.title,
                'content': article.text,
                'authors': article.authors,
                'publish_date': article.publish_date,
                'top_image': article.top_image,
                'keywords': article.keywords if hasattr(article, 'keywords') else []
            }

            return content_data

        except Exception as e:
            self.logger.error(f"Error extracting article content from {url}: {e}")
            return None


class IndianNewsRSSConfig:
    """
    Configuration for major Indian news RSS feeds
    """

    FEEDS = {
        'economic_times': {
            'name': 'Economic Times',
            'feeds': [
                'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
                'https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms',
                'https://economictimes.indiatimes.com/news/economy/rssfeeds/1898055.cms',
            ]
        },
        'business_standard': {
            'name': 'Business Standard',
            'feeds': [
                'https://www.business-standard.com/rss/markets-106.rss',
                'https://www.business-standard.com/rss/finance-101.rss',
                'https://www.business-standard.com/rss/economy-policy-102.rss',
            ]
        },
        'livemint': {
            'name': 'LiveMint',
            'feeds': [
                'https://www.livemint.com/rss/markets',
                'https://www.livemint.com/rss/companies',
                'https://www.livemint.com/rss/economy',
            ]
        },
        'moneycontrol': {
            'name': 'MoneyControl',
            'feeds': [
                'https://www.moneycontrol.com/rss/latestnews.xml',
                'https://www.moneycontrol.com/rss/marketedge.xml',
            ]
        },
        'the_hindu_business': {
            'name': 'The Hindu Business',
            'feeds': [
                'https://www.thehindu.com/business/markets/feeder/default.rss',
                'https://www.thehindu.com/business/Economy/feeder/default.rss',
                'https://www.thehindu.com/business/Industry/feeder/default.rss',
            ]
        },
        'times_of_india_business': {
            'name': 'Times of India Business',
            'feeds': [
                'https://timesofindia.indiatimes.com/rssfeeds/1898055.cms',
            ]
        }
    }

    @classmethod
    def get_scraper(cls, source_key: str) -> Optional[RSSFeedScraper]:
        """
        Get RSS scraper for a specific source

        Args:
            source_key: Key identifying the news source

        Returns:
            RSSFeedScraper instance or None if source not found
        """
        if source_key not in cls.FEEDS:
            return None

        config = cls.FEEDS[source_key]
        return RSSFeedScraper(
            source_name=config['name'],
            feed_urls=config['feeds']
        )

    @classmethod
    def get_all_scrapers(cls) -> List[RSSFeedScraper]:
        """
        Get RSS scrapers for all configured sources

        Returns:
            List of RSSFeedScraper instances
        """
        return [cls.get_scraper(key) for key in cls.FEEDS.keys()]
