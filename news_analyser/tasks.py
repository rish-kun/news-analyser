# Standard library imports
import logging
import os

# Third-party imports
from celery import shared_task
import google.generativeai as genai

# Local application imports
from .exceptions import GeminiAPIError
from .models import News
from .prompts import news_analysis_prompt

# Configure logging
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyse_news_task(self, news_id):
    """
    Celery task to analyze the sentiment of a news article using the Gemini API.

    Args:
        news_id (int): The ID of the News object to analyze.
    """
    logger.info(f"Analyzing news item with id: {news_id}")
    try:
        news = News.objects.get(id=news_id)
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")

        genai.configure(api_key=api_key)

        prompt = news_analysis_prompt.format(
            title=news.title,
            content_summary=news.content_summary,
            content=news.content or ""
        )

        try:
            model = genai.GenerativeModel('gemini-pro')
            analysis = model.generate_content(prompt)

            # Assuming the API returns a float in a string
            news.impact_rating = float(analysis.text)
            news.save()
            logger.info(f"Successfully analyzed news item {news_id}.")

        except Exception as exc:
            logger.error(f"Gemini API call failed for news_id {news_id}: {exc}")
            raise self.retry(exc=exc)

    except News.DoesNotExist:
        logger.warning(f"News item with id {news_id} not found.")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.critical(f"An unexpected error occurred while analyzing news item {news_id}: {e}", exc_info=True)
