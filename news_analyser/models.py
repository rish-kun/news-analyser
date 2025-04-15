import asyncio
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

    def analyse_news(self):
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = news_analysis_prompt.format(
            title=self.title, content_summary=self.content_summary, content=self.content)
        while True:
            try:
                analysis = client.models.generate_content(
                    model="gemini-2.0-flash-thinking-exp-01-21", contents=prompt)
                self.impact_rating = float(analysis.text)
                self.save()
            except genai.errors.ClientError:
                alt_api_key = os.getenv("GEMINI_API_KEY_2")
                client2 = genai.Client(api_key=alt_api_key)
                analysis = client2.models.generate_content(
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


class Source(models.Model):
    id_name = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    url = models.URLField()

    def __str__(self):
        return self.name
