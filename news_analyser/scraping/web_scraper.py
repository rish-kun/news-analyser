"""
Web scraper using BeautifulSoup for parsing HTML
"""

import asyncio
import logging
from typing import List, Dict, Optional
import aiohttp
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WebScraper(BaseScraper):
    """
    Web scraper using BeautifulSoup for HTML parsing
    """

    # User agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]

    def __init__(self, source_name: str, base_url: str, selectors: Dict[str, str], timeout: int = 30):
        """
        Initialize web scraper

        Args:
            source_name: Name of the news source
            base_url: Base URL of the website
            selectors: Dictionary of CSS selectors for parsing
            timeout: Request timeout in seconds
        """
        super().__init__(source_name, base_url)
        self.selectors = selectors
        self.timeout = timeout
        self.current_user_agent = 0

    def _get_user_agent(self) -> str:
        """Rotate user agent"""
        user_agent = self.USER_AGENTS[self.current_user_agent]
        self.current_user_agent = (self.current_user_agent + 1) % len(self.USER_AGENTS)
        return user_agent

    async def scrape(self) -> List[Dict]:
        """
        Scrape news articles from the website

        Returns:
            List of article dictionaries
        """
        try:
            headers = {'User-Agent': self._get_user_agent()}

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(self.source_url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to fetch {self.source_url}: HTTP {response.status}")
                        return []

                    html = await response.text()

            # Parse HTML
            soup = BeautifulSoup(html, 'lxml')
            articles = self._parse_article_list(soup)

            self.logger.info(f"Scraped {len(articles)} articles from {self.source_name}")

            # Normalize and validate
            normalized_articles = []
            for article in articles:
                if self.validate_article(article):
                    normalized_articles.append(self.normalize_article(article))

            return normalized_articles

        except Exception as e:
            self.logger.error(f"Error scraping {self.source_url}: {e}")
            return []

    def _parse_article_list(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse article list from HTML

        Args:
            soup: BeautifulSoup object

        Returns:
            List of raw article dictionaries
        """
        articles = []

        # Find all article containers
        article_elements = soup.select(self.selectors.get('article_container', 'article'))

        for element in article_elements:
            try:
                article = {}

                # Extract title
                title_selector = self.selectors.get('title', 'h2, h3')
                title_elem = element.select_one(title_selector)
                if title_elem:
                    article['title'] = title_elem.get_text(strip=True)

                # Extract link
                link_selector = self.selectors.get('link', 'a')
                link_elem = element.select_one(link_selector)
                if link_elem and link_elem.get('href'):
                    article['link'] = self._normalize_url(link_elem['href'])

                # Extract summary
                summary_selector = self.selectors.get('summary', 'p')
                summary_elem = element.select_one(summary_selector)
                if summary_elem:
                    article['summary'] = summary_elem.get_text(strip=True)

                # Extract image
                image_selector = self.selectors.get('image', 'img')
                image_elem = element.select_one(image_selector)
                if image_elem:
                    article['image_url'] = image_elem.get('src', image_elem.get('data-src', ''))

                # Extract publish date
                date_selector = self.selectors.get('date', 'time')
                date_elem = element.select_one(date_selector)
                if date_elem:
                    article['published'] = date_elem.get('datetime', date_elem.get_text(strip=True))

                if article.get('title') and article.get('link'):
                    articles.append(article)

            except Exception as e:
                self.logger.warning(f"Error parsing article element: {e}")
                continue

        return articles

    async def scrape_article_content(self, url: str) -> Optional[Dict]:
        """
        Scrape full content from article URL

        Args:
            url: Article URL

        Returns:
            Dictionary with article content
        """
        try:
            headers = {'User-Agent': self._get_user_agent()}

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to fetch article {url}: HTTP {response.status}")
                        return None

                    html = await response.text()

            soup = BeautifulSoup(html, 'lxml')

            content_data = {
                'title': self._extract_title(soup),
                'content': self._extract_content(soup),
                'author': self._extract_author(soup),
                'publish_date': self._extract_date(soup),
                'image_url': self._extract_image(soup)
            }

            return content_data

        except Exception as e:
            self.logger.error(f"Error scraping article content from {url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title"""
        selectors = ['h1.article-title', 'h1', 'meta[property="og:title"]']

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == 'meta':
                    return elem.get('content', '')
                return elem.get_text(strip=True)

        return ''

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract article content"""
        selectors = [
            'div.article-content',
            'div.story-content',
            'article',
            'div[itemprop="articleBody"]'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                # Remove scripts and styles
                for tag in elem(['script', 'style', 'aside', 'nav']):
                    tag.decompose()

                # Get text from all paragraphs
                paragraphs = elem.find_all('p')
                return '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

        return ''

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract article author"""
        selectors = [
            'span.author',
            'a.author',
            'meta[name="author"]',
            'div.author'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == 'meta':
                    return elem.get('content', '')
                return elem.get_text(strip=True)

        return ''

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publish date"""
        selectors = [
            'time',
            'meta[property="article:published_time"]',
            'span.publish-date'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == 'meta':
                    return elem.get('content', '')
                return elem.get('datetime', elem.get_text(strip=True))

        return ''

    def _extract_image(self, soup: BeautifulSoup) -> str:
        """Extract main article image"""
        selectors = [
            'meta[property="og:image"]',
            'img.article-image',
            'img.main-image'
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                if elem.name == 'meta':
                    return elem.get('content', '')
                return elem.get('src', elem.get('data-src', ''))

        return ''

    def _normalize_url(self, url: str) -> str:
        """Normalize relative URLs to absolute"""
        if url.startswith('http'):
            return url
        elif url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return self.source_url.rstrip('/') + url
        else:
            return self.source_url.rstrip('/') + '/' + url
