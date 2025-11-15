# Standard library imports
from email.utils import parsedate_to_datetime

# Django imports
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

# Local application imports
from .utils.scraper import get_news


class Keyword(models.Model):
    """Represents a search term for news queries."""
    name = models.CharField(max_length=200)
    create_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Returns the name of the keyword."""
        return self.name

    def get_news(self):
        """Returns a dictionary of news articles related to this keyword."""
        return {self: self.news.all()}


class UserProfile(models.Model):
    """Represents a user's profile, including preferences and watchlist."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    preferences = models.JSONField(default=dict, blank=True)
    stocks = models.ManyToManyField('Stock', blank=True)
    searches = models.ManyToManyField(
        Keyword, blank=True, related_name="users")

    def __str__(self):
        """Returns the username of the user."""
        return f"Profile of {self.user.username}"


class News(models.Model):
    """Represents a news article with its sentiment and other metadata."""
    title = models.CharField(max_length=200)
    content_summary = models.TextField()
    content = models.TextField(null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    link = models.CharField(max_length=200, unique=True)
    keyword = models.ForeignKey(
        Keyword, on_delete=models.CASCADE, related_name="news")
    impact_rating = models.FloatField(default=0)
    source = models.ForeignKey(
        "Source", on_delete=models.CASCADE, related_name="news", default=None, null=True)

    def __str__(self):
        """Returns the title of the news article."""
        return self.title

    @staticmethod
    def parse_news(news_data, kwd):
        """
        Parses news data and creates or updates a News object.

        Args:
            news_data (dict): A dictionary containing news article data.
            kwd (Keyword): The keyword associated with this news.

        Returns:
            News: The created or updated News object.
        """
        obj, created = News.objects.get_or_create(
            link=news_data['link'],
            defaults={
                'title': news_data['title'],
                'content_summary': news_data['summary'],
                'keyword': kwd,
            }
        )

        if created:
            try:
                date = parsedate_to_datetime(news_data['published'])
                obj.date = date
            except (TypeError, ValueError):
                obj.date = timezone.now()

            if "economictimes" in obj.link:
                obj.source = Source.objects.get(id_name="ET")
            elif "timesofindia" in obj.link:
                obj.source = Source.objects.get(id_name="TOI")
            elif "thehindu" in obj.link:
                obj.source = Source.objects.get(id_name="TH")
            else:
                obj.source = Source.objects.get(id_name="OTHER")

            obj.save()
        return obj

    async def get_content(self):
        """Asynchronously fetches the full content of the news article."""
        self.content = await get_news(self.link)
        await self.asave()
        return self.content


class Sector(models.Model):
    """Represents a stock market sector."""
    name = models.CharField(max_length=200)
    search_fields = models.CharField(max_length=8000, null=True, blank=True)

    def __str__(self):
        """Returns the name of the sector."""
        return self.name


class Stock(models.Model):
    """Represents an NSE-listed stock."""
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=20, unique=True)
    sector = models.ForeignKey(
        Sector, on_delete=models.CASCADE, related_name="stocks", null=True, blank=True)
    keywords = models.ManyToManyField(
        Keyword, blank=True, related_name="stocks")

    def __str__(self):
        """Returns the name of the stock."""
        return self.name


class Source(models.Model):
    """Represents a news source, such as a website or RSS feed."""
    id_name = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200)
    url = models.URLField()

    def __str__(self):
        """Returns the name of the source."""
        return self.name
