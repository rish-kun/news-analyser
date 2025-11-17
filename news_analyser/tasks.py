from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import News, Stock
import json
import logging
from google import genai
import os
from blackbox.settings import GEMINI_API_KEY
from .prompts import news_analysis_prompt

logger = logging.getLogger(__name__)

def _process_gemini_response(response_text, news):
    try:
        response_json = json.loads(response_text)
        news.impact_rating = float(response_json['sentiment_score'])
        tickers = response_json['tickers']
        for ticker in tickers:
            stock, created = Stock.objects.get_or_create(symbol=ticker)
            news.stocks.add(stock)
        logger.info("Analysis complete for news_id: %s", news.id)
        news.save()
        return True
    except json.JSONDecodeError as e:
        logger.error("Error decoding JSON for news_id: %s - %s", news.id, e)
        return False
    except (KeyError, TypeError) as e:
        logger.error("Error processing response for news_id: %s - %s", news.id, e)
        return False

@shared_task
def analyse_news_task(news_id):
    logger.info("Analysing news item with id: %s", news_id)
    try:
        news = News.objects.get(id=news_id)
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = news_analysis_prompt.format(
            title=news.title, content_summary=news.content_summary, content=news.content)
        while True:
            try:
                logger.info("News analysis started for news_id: %s", news_id)
                analysis = client.models.generate_content(
                    model="gemini-2.5-flash-preview-05-20", contents=prompt)
                response_text = analysis.text.strip()
                if _process_gemini_response(response_text, news):
                    break
            except genai.errors.ClientError:
                alt_api_key = os.getenv("GEMINI_API_KEY")
                client2 = genai.Client(api_key=alt_api_key)
                analysis = client2.models.generate_content(
                    model="gemini-2.5-flash-preview-05-20", contents=prompt)
                response_text = analysis.text.strip()
                if _process_gemini_response(response_text, news):
                    break
            except Exception as e:
                logger.error("An unexpected error occurred during analysis for news_id: %s - %s", news_id, e)
                return "Error"
    except News.DoesNotExist:
        logger.warning("News item with id %s not found.", news_id)
    except Exception as e:
        logger.error("An error occurred while analyzing news item %s: %s", news_id, e)
