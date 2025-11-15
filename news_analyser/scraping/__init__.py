"""
News Scraping Module for News Analyser

Provides comprehensive web scraping capabilities for Indian financial news sources
including RSS feeds, web scraping, and Selenium-based scraping.
"""

from .base_scraper import BaseScraper
from .rss_scraper import RSSFeedScraper
from .web_scraper import WebScraper
from .selenium_scraper import SeleniumScraper
from .deduplication import ContentDeduplicator

__all__ = [
    'BaseScraper',
    'RSSFeedScraper',
    'WebScraper',
    'SeleniumScraper',
    'ContentDeduplicator',
]
