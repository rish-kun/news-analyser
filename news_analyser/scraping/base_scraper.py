"""
Base scraper class with common functionality for all scrapers
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all news scrapers
    """

    def __init__(self, source_name: str, source_url: str):
        """
        Initialize base scraper

        Args:
            source_name: Name of the news source
            source_url: Base URL of the source
        """
        self.source_name = source_name
        self.source_url = source_url
        self.logger = logging.getLogger(f"{__name__}.{source_name}")

    @abstractmethod
    async def scrape(self) -> List[Dict]:
        """
        Scrape news articles from the source

        Returns:
            List of dictionaries containing article data
        """
        pass

    @abstractmethod
    async def scrape_article_content(self, url: str) -> Optional[Dict]:
        """
        Scrape full content of a single article

        Args:
            url: URL of the article

        Returns:
            Dictionary with article content or None if failed
        """
        pass

    def normalize_article(self, article: Dict) -> Dict:
        """
        Normalize article data to standard format

        Args:
            article: Raw article data

        Returns:
            Normalized article dictionary
        """
        normalized = {
            'title': article.get('title', '').strip(),
            'content_summary': article.get('summary', article.get('description', '')).strip(),
            'content': article.get('content', ''),
            'link': article.get('link', article.get('url', '')),
            'author': article.get('author', ''),
            'published_at': self._parse_date(article.get('published', article.get('pubDate'))),
            'image_url': article.get('image_url', ''),
            'source_name': self.source_name,
            'tags': article.get('tags', []),
        }

        # Generate content hash for deduplication
        normalized['content_hash'] = self._generate_content_hash(
            normalized['title'],
            normalized['content_summary']
        )

        return normalized

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse date string to datetime object

        Args:
            date_str: Date string in various formats

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str:
            return None

        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            pass

        try:
            import dateparser
            return dateparser.parse(date_str)
        except:
            pass

        return None

    def _generate_content_hash(self, title: str, content: str) -> str:
        """
        Generate hash for content deduplication

        Args:
            title: Article title
            content: Article content/summary

        Returns:
            SHA256 hash of combined content
        """
        combined = f"{title.lower()}{content.lower()}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def validate_article(self, article: Dict) -> bool:
        """
        Validate that article has required fields

        Args:
            article: Article dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = ['title', 'link']

        for field in required_fields:
            if not article.get(field):
                self.logger.warning(f"Article missing required field: {field}")
                return False

        # Validate URL
        if not article['link'].startswith(('http://', 'https://')):
            self.logger.warning(f"Invalid URL: {article['link']}")
            return False

        return True

    async def scrape_with_retry(self, max_retries: int = 3) -> List[Dict]:
        """
        Scrape with retry logic

        Args:
            max_retries: Maximum number of retry attempts

        Returns:
            List of scraped articles
        """
        for attempt in range(max_retries):
            try:
                articles = await self.scrape()
                self.logger.info(f"Successfully scraped {len(articles)} articles from {self.source_name}")
                return articles

            except Exception as e:
                self.logger.error(f"Scraping attempt {attempt + 1} failed for {self.source_name}: {e}")

                if attempt < max_retries - 1:
                    import asyncio
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"All retry attempts exhausted for {self.source_name}")
                    return []

        return []
