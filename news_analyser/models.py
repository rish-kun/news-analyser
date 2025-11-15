from .prompts import news_analysis_prompt
from django.utils import timezone
from django.db import models
from email.utils import parsedate_to_datetime
from blackbox.settings import GEMINI_API_KEY


class Keyword(models.Model):
    name = models.CharField(max_length=200)
    create_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_news(self):
        return {self: self.news.all()}


class UserProfile(models.Model):
    user = models.OneToOneField(
        'auth.User', on_delete=models.CASCADE, related_name='profile')
    preferences = models.JSONField(default=dict, blank=True)
    stocks = models.ManyToManyField('Stock', blank=True)
    searches = models.ManyToManyField(
        Keyword, blank=True, related_name="users")

    def __str__(self):
        return f"Profile of {self.user.username}"


class News(models.Model):
    title = models.CharField(max_length=500)
    content_summary = models.TextField()
    content = models.TextField(null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    link = models.CharField(max_length=500, unique=True)
    keyword = models.ForeignKey(
        Keyword, on_delete=models.CASCADE, related_name="news")
    impact_rating = models.FloatField(default=0)
    source = models.ForeignKey(
        "Source", on_delete=models.CASCADE, related_name="news", default=None, null=True)

    # New fields for enhanced functionality
    author = models.CharField(max_length=200, null=True, blank=True)
    image_url = models.URLField(max_length=1000, null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    is_analyzed = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Tickers mentioned in the article
    tickers = models.ManyToManyField('Stock', blank=True, related_name='news_mentions')
    sectors = models.ManyToManyField('Sector', blank=True, related_name='news_mentions')

    # Content hash for deduplication
    content_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-published_at', '-date']
        indexes = [
            models.Index(fields=['-published_at', 'source']),
            models.Index(fields=['is_analyzed']),
            models.Index(fields=['-scraped_at']),
        ]
        verbose_name_plural = "News"

    def __str__(self):
        return self.title

    @staticmethod
    def parse_news(news, kwd):
        obj, created = News.objects.get_or_create(title=news['title'],
                                                  content_summary=news['summary'],
                                                  link=news['link'],
                                                  keyword=kwd)
        try:
            date = parsedate_to_datetime(news['published'])

        except:
            date = timezone.now()
        if "economc" in obj.link and "times" in obj.link:
            obj.source = Source.objects.get(id_name="ET")
        elif "times" in obj.link and "india" in obj.link and "of" in obj.link:
            obj.source = Source.objects.get(id_name="TOI")
        elif "hindu" in obj.link:
            obj.source = Source.objects.get(id_name="TH")
        else:
            obj.source = Source.objects.get(id_name="OTHER")

        obj.keyword = kwd
        if created:
            obj.date = date
            obj.save()
        return obj

    async def get_content(self):
        from .br_use import get_news
        content = await get_news(self.link)
        return content


class Sector(models.Model):
    name = models.CharField(max_length=200)
    search_fields = models.CharField(max_length=8000, null=True, blank=True)


class Stock(models.Model):
    name = models.CharField(max_length=200)
    symbol = models.CharField(max_length=20)
    sector = models.ForeignKey(
        Sector, on_delete=models.CASCADE, related_name="stocks", null=True, blank=True)
    keywords = models.ManyToManyField(
        Keyword, blank=True, related_name="stocks")


class Source(models.Model):
    id_name = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    url = models.URLField()
    is_active = models.BooleanField(default=True)
    scrape_frequency = models.IntegerField(default=30, help_text="Scraping frequency in minutes")
    last_scraped = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class SentimentScore(models.Model):
    """Stores detailed sentiment analysis for news articles"""
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name='sentiment_scores')
    ticker = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True, blank=True, related_name='sentiment_scores')
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, null=True, blank=True, related_name='sentiment_scores')

    # Sentiment scores from different models
    gemini_score = models.FloatField(null=True, blank=True)
    finbert_score = models.FloatField(null=True, blank=True)
    vader_score = models.FloatField(null=True, blank=True)
    textblob_score = models.FloatField(null=True, blank=True)

    # Composite/final score
    sentiment_score = models.FloatField(db_index=True)
    sentiment_label = models.CharField(max_length=20, choices=[
        ('very_negative', 'Very Negative'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('positive', 'Positive'),
        ('very_positive', 'Very Positive'),
    ])

    # Confidence and metadata
    confidence = models.FloatField(default=0.0)
    analysis_details = models.JSONField(default=dict, blank=True)

    # Entity extraction
    entities = models.JSONField(default=list, blank=True, help_text="Extracted entities (companies, people, locations)")
    keywords_extracted = models.JSONField(default=list, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    model_used = models.CharField(max_length=50, default='ensemble')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticker', '-created_at']),
            models.Index(fields=['sector', '-created_at']),
            models.Index(fields=['sentiment_score']),
            models.Index(fields=['-created_at']),
        ]
        unique_together = [['news', 'ticker'], ['news', 'sector']]

    def __str__(self):
        target = self.ticker.symbol if self.ticker else (self.sector.name if self.sector else "General")
        return f"{self.news.title[:50]} - {target}: {self.sentiment_score}"

    @classmethod
    def get_sentiment_label(cls, score):
        """Convert numerical score to sentiment label"""
        if score <= -0.6:
            return 'very_negative'
        elif score <= -0.2:
            return 'negative'
        elif score <= 0.2:
            return 'neutral'
        elif score <= 0.6:
            return 'positive'
        else:
            return 'very_positive'
