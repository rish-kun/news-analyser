from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import News
from google import genai
import os
from blackbox.settings import GEMINI_API_KEY
from .prompts import news_analysis_prompt


@shared_task
def analyse_news_task(news_id):
    try:
        news = News.objects.get(id=news_id)
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = news_analysis_prompt.format(
            title=news.title, content_summary=news.content_summary, content=news.content)
        while True:
            try:
                analysis = client.models.generate_content(
                    model="gemini-2.0-flash-thinking-exp-01-21", contents=prompt)
                news.impact_rating = float(analysis.text)
                news.save()
            except genai.errors.ClientError:
                alt_api_key = os.getenv("GEMINI_API_KEY_2")
                client2 = genai.Client(api_key=alt_api_key)
                analysis = client2.models.generate_content(
                    model="gemini-2.0-flash-thinking-exp-01-21", contents=prompt)
                news.impact_rating = float(analysis.text)
                news.save()
            except Exception as e:
                print(e)
                return "Error"
            else:
                break
    except News.DoesNotExist:
        # Handle case where news item is not found
        print(f"News item with id {news_id} not found.")
    except Exception as e:
        # Handle other potential exceptions
        print(f"An error occurred while analyzing news item {news_id}: {e}")
