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
    title = models.CharField(max_length=200)
    content_summary = models.TextField()
    content = models.TextField(null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    link = models.CharField(max_length=200, unique=True)
    keywords = models.ManyToManyField(Keyword, related_name="news")
    impact_rating = models.FloatField(default=0)
    source = models.ForeignKey(
        "Source", on_delete=models.CASCADE, related_name="news", default=None, null=True)

    def __str__(self):
        return self.title

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

    def __str__(self):
        return self.name
