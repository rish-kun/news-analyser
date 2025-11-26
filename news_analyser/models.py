"""
Django models for the News Analyser application.
This module defines the database models for storing news articles,
keywords, stocks, user profiles, and related metadata.
"""

from .prompts import news_analysis_prompt
from django.utils import timezone
from django.db import models
from email.utils import parsedate_to_datetime
from blackbox.settings import GEMINI_API_KEY
import logging

logger = logging.getLogger(__name__)


class Keyword(models.Model):
    """
    Keyword or search term for news queries.

    Attributes:
        name (str): The keyword text
        create_date (datetime): When the keyword was first created
    """
    name = models.CharField(max_length=200, db_index=True)
    create_date = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-create_date']
        indexes = [
            models.Index(fields=['name', 'create_date']),
        ]

    def __str__(self):
        return self.name

    def get_news(self):
        """Get all news articles associated with this keyword."""
        return {self: self.news.all()}


class UserProfile(models.Model):
    """
    Extended user profile with preferences and watchlist.

    Attributes:
        user (User): One-to-one relationship with Django User
        preferences (dict): JSON field for user settings
        stocks (ManyToMany): User's watchlist stocks
        searches (ManyToMany): User's past search keywords
    """
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='profile',
        db_index=True
    )
    preferences = models.JSONField(default=dict, blank=True)
    stocks = models.ManyToManyField('Stock', blank=True, related_name='users')
    searches = models.ManyToManyField(
        Keyword, blank=True, related_name="users")

    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Profile of {self.user.username}"


class News(models.Model):
    """
    News article with sentiment analysis.

    Attributes:
        title (str): Article headline
        content_summary (str): Brief summary/excerpt
        content (str): Full article content (optional)
        date (datetime): Publication date
        link (str): URL to original article
        keyword (ForeignKey): Associated search keyword
        impact_rating (float): Sentiment score (-1 to 1)
        source (ForeignKey): News source
        sentiment_explanation (str): Why this sentiment was assigned
        sentiment_confidence (float): Model confidence in sentiment (0-1)
        mentioned_tickers (list): Stock symbols mentioned in article
        raw_gemini_response (dict): Full API response for debugging
    """
    title = models.CharField(max_length=500)
    content_summary = models.TextField()
    content = models.TextField(null=True, blank=True)
    date = models.DateTimeField(default=timezone.now, db_index=True)
    link = models.CharField(max_length=500, unique=True, db_index=True)
    keyword = models.ForeignKey(
        Keyword, on_delete=models.CASCADE, related_name="news", db_index=True)
    impact_rating = models.FloatField(default=0, db_index=True)
    source = models.ForeignKey(
        "Source", on_delete=models.CASCADE, related_name="news", default=None, null=True)

    # Enhanced sentiment analysis fields
    sentiment_explanation = models.TextField(null=True, blank=True)
    sentiment_confidence = models.FloatField(default=0, null=True, blank=True)
    mentioned_tickers = models.JSONField(default=list, blank=True)
    raw_gemini_response = models.JSONField(default=dict, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "News"
        indexes = [
            models.Index(fields=['keyword', 'date']),
            models.Index(fields=['impact_rating']),
            models.Index(fields=['-date']),
            models.Index(fields=['source', 'date']),
        ]

    def __str__(self):
        return self.title

    @staticmethod
    def parse_news(news, kwd):
        """
        Parse and save a news entry from RSS feed.

        Args:
            news (dict): RSS entry with title, summary, link, published
            kwd (Keyword): Associated keyword object

        Returns:
            News: Created or existing News object
        """
        try:
            # Get or create news object (avoid duplicates by link)
            obj, created = News.objects.get_or_create(
                link=news['link'],
                defaults={
                    'title': news['title'],
                    'content_summary': news.get('summary', ''),
                    'keyword': kwd
                }
            )

            if not created:
                logger.debug(f"News already exists: {obj.link}")
                return obj

            # Parse publication date
            try:
                date = parsedate_to_datetime(news['published'])
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Failed to parse date for {news['link']}: {e}")
                date = timezone.now()

            # Detect source from URL
            link_lower = obj.link.lower()
            try:
                if "economictimes" in link_lower or "cfo.economictimes" in link_lower:
                    obj.source = Source.objects.get_or_create(
                        id_name="ET",
                        defaults={
                            'name': 'Economic Times',
                            'url': 'https://economictimes.indiatimes.com'
                        }
                    )[0]
                elif "timesofindia" in link_lower:
                    obj.source = Source.objects.get_or_create(
                        id_name="TOI",
                        defaults={
                            'name': 'Times of India',
                            'url': 'https://timesofindia.indiatimes.com'
                        }
                    )[0]
                elif "thehindu" in link_lower:
                    obj.source = Source.objects.get_or_create(
                        id_name="TH",
                        defaults={
                            'name': 'The Hindu',
                            'url': 'https://www.thehindu.com'
                        }
                    )[0]
                elif "moneycontrol" in link_lower:
                    obj.source = Source.objects.get_or_create(
                        id_name="MC",
                        defaults={
                            'name': 'MoneyControl',
                            'url': 'https://www.moneycontrol.com'
                        }
                    )[0]
                elif "business-standard" in link_lower:
                    obj.source = Source.objects.get_or_create(
                        id_name="BS",
                        defaults={
                            'name': 'Business Standard',
                            'url': 'https://www.business-standard.com'
                        }
                    )[0]
                elif "livemint" in link_lower:
                    obj.source = Source.objects.get_or_create(
                        id_name="MINT",
                        defaults={
                            'name': 'Live Mint',
                            'url': 'https://www.livemint.com'
                        }
                    )[0]
                elif "cnbctv18" in link_lower:
                    obj.source = Source.objects.get_or_create(
                        id_name="CNBC",
                        defaults={
                            'name': 'CNBC TV18',
                            'url': 'https://www.cnbctv18.com'
                        }
                    )[0]
                else:
                    obj.source = Source.objects.get_or_create(
                        id_name="OTHER",
                        defaults={
                            'name': 'Other Source',
                            'url': ''
                        }
                    )[0]
            except Exception as e:
                logger.error(f"Error setting source: {e}")
                obj.source = Source.objects.get_or_create(
                    id_name="OTHER",
                    defaults={'name': 'Other Source', 'url': ''}
                )[0]

            obj.keyword = kwd
            obj.date = date
            obj.save()
            logger.info(f"Created new news entry: {obj.title[:50]}...")
            return obj

        except Exception as e:
            logger.error(f"Error parsing news: {e}", exc_info=True)
            raise

    async def get_content(self):
        """
        Extract full article content using browser automation.

        Returns:
            dict: Content extraction result
        """
        from .br_use import get_news
        try:
            content = await get_news(self.link)
            return content
        except Exception as e:
            logger.error(f"Failed to extract content from {self.link}: {e}")
            return {'content': '', 'error': str(e)}


class Sector(models.Model):
    """
    Stock market sector/industry classification.

    Attributes:
        name (str): Sector name (e.g., IT, Banking, Pharma)
        search_fields (str): Additional keywords for sector search
    """
    name = models.CharField(max_length=200, unique=True, db_index=True)
    search_fields = models.CharField(max_length=8000, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Stock(models.Model):
    """
    NSE-listed stock information.

    Attributes:
        name (str): Company name
        symbol (str): NSE stock symbol (e.g., RELIANCE, TCS)
        sector (ForeignKey): Associated sector
        keywords (ManyToMany): Related search keywords
    """
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=20, unique=True, db_index=True)
    sector = models.ForeignKey(
        Sector, on_delete=models.CASCADE, related_name="stocks", null=True, blank=True)
    keywords = models.ManyToManyField(
        Keyword, blank=True, related_name="stocks")

    class Meta:
        ordering = ['symbol']
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['sector', 'symbol']),
        ]

    def __str__(self):
        return f"{self.symbol} - {self.name}"


class Source(models.Model):
    """
    News source metadata.

    Attributes:
        id_name (str): Short identifier (e.g., ET, TOI, TH)
        name (str): Full source name
        url (str): Source website URL
    """
    id_name = models.CharField(max_length=200, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    url = models.URLField()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
