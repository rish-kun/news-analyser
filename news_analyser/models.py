from .prompts import news_analysis_prompt
from django.utils import timezone
from django.db import models
from email.utils import parsedate_to_datetime
from google import genai
import os
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
    searches = models.ManyToManyField(Keyword, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class News(models.Model):
    title = models.CharField(max_length=200)
    content_summary = models.TextField()
    content = models.TextField(null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)
    link = models.CharField(max_length=200)
    keyword = models.ForeignKey(
        Keyword, on_delete=models.CASCADE, related_name="news")
    impact_rating = models.FloatField(default=0)
    source = models.ForeignKey(
        "Source", on_delete=models.CASCADE, related_name="news", default=None, null=True)

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

    def analyse_news(self, user=None):
        api_key = GEMINI_API_KEY
        if user and hasattr(user, 'profile') and user.profile.preferences.get('gemini_api_key'):
            api_key = user.profile.preferences.get('gemini_api_key')

        if not api_key:
            return

        client = genai.Client(api_key=api_key)
        prompt = news_analysis_prompt.format(
            title=self.title, content_summary=self.content_summary, content=self.content)
        while True:
            try:
                analysis = client.models.generate_content(
                    model="gemini-2.0-flash-thinking-exp-01-21", contents=prompt)
                self.impact_rating = float(analysis.text)
                self.save()
            except Exception as e:
                print(e)
                return "Error"
            else:
                break

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
