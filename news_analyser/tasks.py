from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import News
import google.generativeai as genai
import os
from blackbox.settings import GEMINI_API_KEY
from .prompts import news_analysis_prompt
from .exceptions import GeminiAPIError, NewsAnalysisError


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyse_news_task(self, news_id):
    print("Analysing news item with id:", news_id)
    try:
        news = News.objects.get(id=news_id)
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = news_analysis_prompt.format(
            title=news.title, content_summary=news.content_summary, content=news.content)

        try:
            print("news analysis started")
            analysis = client.models.generate_content(
                model="gemini-2.5-flash-preview-05-20", contents=prompt)
            news.impact_rating = float(analysis.text)
            print("analysis done")
            news.save()
        except genai.errors.ClientError as e:
            raise self.retry(exc=GeminiAPIError(f"Gemini API client error: {e}"))
        except Exception as e:
            raise self.retry(exc=NewsAnalysisError(f"An unexpected error occurred during news analysis: {e}"))

    except News.DoesNotExist:
        # Handle case where news item is not found
        print(f"News item with id {news_id} not found.")
    except Exception as e:
        # Handle other potential exceptions
        print(f"An error occurred while analyzing news item {news_id}: {e}")
