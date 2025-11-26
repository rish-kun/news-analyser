from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import News
from google import genai
import logging
import json
from blackbox.settings import GEMINI_API_KEYS
from .prompts import news_analysis_prompt
from .exceptions import (
    GeminiAPIError,
    GeminiRateLimitError,
    GeminiAuthenticationError,
    InvalidSentimentScoreError
)

logger = logging.getLogger(__name__)


def strip_markdown_json(text):
    """
    Strip markdown code block syntax from JSON responses.
    
    Handles responses like:
    ```json
    {"key": "value"}
    ```
    
    Args:
        text (str): Response text that may contain markdown code blocks
        
    Returns:
        str: Cleaned JSON text
    """
    text = text.strip()
    # Remove markdown code block markers
    if text.startswith('```'):
        # Find the end of the opening marker (```json or just ```)
        first_newline = text.find('\n')
        if first_newline != -1:
            text = text[first_newline + 1:]
        
        # Remove closing ```
        if text.endswith('```'):
            text = text[:-3]
    
    return text.strip()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyse_news_task(self, news_id):
    """
    Analyze news sentiment using Gemini API.

    Args:
        news_id (int): The ID of the News object to analyze

    Returns:
        dict: Analysis results including sentiment score and metadata

    Raises:
        GeminiAPIError: If API calls fail after retries
        InvalidSentimentScoreError: If sentiment score is out of range
    """
    logger.info(f"Starting sentiment analysis for news ID: {news_id}")

    try:
        news = News.objects.get(id=news_id)
        logger.debug(f"Retrieved news object: {news.title[:50]}...")

        # Try primary API key first
        api_keys = GEMINI_API_KEYS
        # api_keys = [key for key in api_keys if key]  # Filter out None values - already handled in settings

        if not api_keys:
            logger.critical("No Gemini API keys configured!")
            raise GeminiAuthenticationError("No API keys available")

        prompt = news_analysis_prompt.format(
            title=news.title,
            content_summary=news.content_summary,
            content=news.content or ""
        )

        last_error = None
        for idx, api_key in enumerate(api_keys):
            try:
                logger.debug(f"Attempting analysis with API key #{idx + 1}")
                client = genai.Client(api_key=api_key)

                # Update task state to show progress
                self.update_state(
                    state='PROGRESS',
                    meta={'current': idx + 1, 'total': len(api_keys), 'status': 'Analyzing...'}
                )

                analysis = client.models.generate_content(
                    # model="gemini-2.5-flash",
                    # model="gemini-3-pro-preview",
                    model="gemini-flash-lite-latest",
                    contents=prompt
                )

                # Parse structured JSON response
                response_text = analysis.text.strip()
                logger.debug(f"Gemini response: {response_text[:200]}...")

                try:
                    # Strip markdown code blocks if present
                    cleaned_response = strip_markdown_json(response_text)
                    logger.debug(f"Cleaned response: {cleaned_response[:200]}...")
                    
                    # Try to parse as JSON
                    analysis_data = json.loads(cleaned_response)

                    # Extract and validate sentiment score
                    sentiment_score = float(analysis_data.get('sentiment', 0))
                    if not -1 <= sentiment_score <= 1:
                        logger.error(f"Sentiment score out of range: {sentiment_score}")
                        raise InvalidSentimentScoreError(f"Sentiment {sentiment_score} not in [-1, 1]")

                    # Extract additional fields
                    confidence = float(analysis_data.get('confidence', 0))
                    explanation = analysis_data.get('explanation', '')
                    tickers = analysis_data.get('tickers', [])
                    impact_timeline = analysis_data.get('impact_timeline', '')

                    # Update news object with all fields
                    news.impact_rating = sentiment_score
                    news.sentiment_confidence = confidence
                    news.sentiment_explanation = explanation
                    news.mentioned_tickers = tickers if isinstance(tickers, list) else []
                    news.raw_gemini_response = analysis_data
                    news.save()

                    logger.info(
                        f"Successfully analyzed news ID {news_id}. "
                        f"Sentiment: {sentiment_score:.3f}, Confidence: {confidence:.3f}, "
                        f"Tickers: {tickers}"
                    )

                    return {
                        'status': 'success',
                        'news_id': news_id,
                        'sentiment_score': sentiment_score,
                        'confidence': confidence,
                        'tickers': tickers,
                        'api_key_used': idx + 1
                    }

                except json.JSONDecodeError:
                    # Fallback: Try to parse as simple float
                    logger.warning(f"Failed to parse JSON, trying simple float: {response_text[:100]}")
                    try:
                        sentiment_score = float(response_text)
                        if not -1 <= sentiment_score <= 1:
                            raise InvalidSentimentScoreError(f"Sentiment {sentiment_score} not in [-1, 1]")

                        news.impact_rating = sentiment_score
                        news.save()

                        logger.info(f"Successfully analyzed news ID {news_id} (simple mode). Sentiment: {sentiment_score:.3f}")

                        return {
                            'status': 'success',
                            'news_id': news_id,
                            'sentiment_score': sentiment_score,
                            'api_key_used': idx + 1
                        }
                    except ValueError as e:
                        logger.error(f"Failed to parse response as float: {response_text}")
                        raise InvalidSentimentScoreError(f"Invalid response: {response_text}")

            except genai.errors.ClientError as e:
                error_msg = str(e)
                logger.warning(
                    f"Gemini API error with key #{idx + 1}: {error_msg}"
                )
                last_error = e

                # Check if it's a rate limit error
                if "429" in error_msg or "quota" in error_msg.lower():
                    logger.warning(f"Rate limit hit for API key #{idx + 1}")
                    if idx < len(api_keys) - 1:
                        continue  # Try next key
                    else:
                        raise GeminiRateLimitError("All API keys rate limited")

                # Check if it's an authentication error
                if "401" in error_msg or "403" in error_msg:
                    logger.error(f"Authentication failed for API key #{idx + 1}")
                    continue  # Try next key

                # For other errors, try next key
                continue

            except Exception as e:
                logger.error(
                    f"Unexpected error during analysis with key #{idx + 1}: {e}",
                    exc_info=True
                )
                last_error = e
                continue

        # If we've exhausted all keys, raise the last error
        if last_error:
            logger.error(f"All API keys failed for news ID {news_id}")
            raise GeminiAPIError(f"Analysis failed: {last_error}")

    except News.DoesNotExist:
        logger.error(f"News item with ID {news_id} not found in database")
        return {
            'status': 'error',
            'news_id': news_id,
            'error': 'News not found'
        }

    except (GeminiRateLimitError, GeminiAuthenticationError) as exc:
        # Retry with exponential backoff
        logger.warning(
            f"Retrying task for news ID {news_id}. "
            f"Attempt {self.request.retries + 1}/{self.max_retries}"
        )
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    except Exception as e:
        logger.critical(
            f"Fatal error analyzing news ID {news_id}: {e}",
            exc_info=True
        )
        return {
            'status': 'error',
            'news_id': news_id,
            'error': str(e)
        }
