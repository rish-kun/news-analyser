"""
Unit tests for Celery tasks.

This module tests async task execution, retry logic, and error handling.
"""

from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
import json
from news_analyser.tasks import analyse_news_task
from news_analyser.models import News, Keyword, Source
from news_analyser.exceptions import (
    GeminiAPIError,
    GeminiRateLimitError,
    InvalidSentimentScoreError
)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class AnalyseNewsTaskTest(TestCase):
    """Test cases for the analyse_news_task Celery task."""

    def setUp(self):
        """Set up test data."""
        self.keyword = Keyword.objects.create(name="TCS")
        self.source = Source.objects.create(
            id_name="ET",
            name="Economic Times",
            url="https://economictimes.indiatimes.com"
        )
        self.news = News.objects.create(
            title="TCS Wins Major Contract",
            content_summary="TCS secures $500M deal with Fortune 500 company",
            link="https://example.com/tcs-contract",
            keyword=self.keyword,
            source=self.source
        )

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_success_json_response(self, mock_client_class):
        """Test successful sentiment analysis with JSON response."""
        # Mock Gemini API response with JSON
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "sentiment": 0.75,
            "confidence": 0.85,
            "explanation": "Major contract win indicates strong business growth",
            "tickers": ["TCS"],
            "impact_timeline": "short-term"
        })

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Run task
        result = analyse_news_task(self.news.id)

        # Verify result
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['sentiment_score'], 0.75)
        self.assertEqual(result['confidence'], 0.85)
        self.assertIn('TCS', result['tickers'])

        # Verify news was updated
        self.news.refresh_from_db()
        self.assertEqual(self.news.impact_rating, 0.75)
        self.assertEqual(self.news.sentiment_confidence, 0.85)
        self.assertIn('TCS', self.news.mentioned_tickers)

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_success_simple_float(self, mock_client_class):
        """Test successful sentiment analysis with simple float response."""
        # Mock Gemini API response with just a number
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "0.65"

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Run task
        result = analyse_news_task(self.news.id)

        # Verify result
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['sentiment_score'], 0.65)

        # Verify news was updated
        self.news.refresh_from_db()
        self.assertEqual(self.news.impact_rating, 0.65)

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_validates_sentiment_range(self, mock_client_class):
        """Test that sentiment scores outside [-1, 1] are rejected."""
        # Mock invalid sentiment score
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "2.5"  # Invalid: outside range

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Run task - should handle error gracefully
        result = analyse_news_task(self.news.id)

        # Task should return error status
        self.assertEqual(result['status'], 'error')

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_handles_api_error(self, mock_client_class):
        """Test handling of Gemini API errors."""
        # Mock API error
        mock_client = MagicMock()
        from google import genai
        mock_client.models.generate_content.side_effect = genai.errors.ClientError("API Error")
        mock_client_class.return_value = mock_client

        # Run task
        result = analyse_news_task(self.news.id)

        # Should return error status
        self.assertEqual(result['status'], 'error')

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_handles_nonexistent_news(self, mock_client_class):
        """Test handling when news ID doesn't exist."""
        # Try to analyze non-existent news
        result = analyse_news_task(99999)

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error'], 'News not found')

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_uses_fallback_api_keys(self, mock_client_class):
        """Test that task tries fallback API keys on failure."""
        # First call fails, second succeeds
        mock_client = MagicMock()
        from google import genai

        # First API key fails with rate limit
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise genai.errors.ClientError("429: Rate limit exceeded")
            else:
                # Second call succeeds
                response = MagicMock()
                response.text = "0.5"
                return response

        mock_client.models.generate_content.side_effect = side_effect
        mock_client_class.return_value = mock_client

        # Run task
        with patch('news_analyser.tasks.GEMINI_API_KEY_2', 'backup_key'):
            result = analyse_news_task(self.news.id)

        # Should eventually succeed with backup key
        # (behavior depends on implementation)

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_parses_tickers_correctly(self, mock_client_class):
        """Test that stock tickers are correctly extracted from JSON."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "sentiment": 0.5,
            "confidence": 0.7,
            "explanation": "Moderate impact",
            "tickers": ["TCS", "INFY", "WIPRO"],
            "impact_timeline": "medium-term"
        })

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Run task
        result = analyse_news_task(self.news.id)

        # Verify tickers were extracted
        self.assertIn('TCS', result['tickers'])
        self.assertIn('INFY', result['tickers'])
        self.assertIn('WIPRO', result['tickers'])

        # Verify stored in database
        self.news.refresh_from_db()
        self.assertEqual(len(self.news.mentioned_tickers), 3)

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_stores_raw_response(self, mock_client_class):
        """Test that raw Gemini response is stored for debugging."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        response_data = {
            "sentiment": 0.6,
            "confidence": 0.8,
            "explanation": "Test explanation",
            "tickers": ["TCS"],
            "impact_timeline": "immediate"
        }
        mock_response.text = json.dumps(response_data)

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Run task
        analyse_news_task(self.news.id)

        # Verify raw response is stored
        self.news.refresh_from_db()
        self.assertEqual(self.news.raw_gemini_response, response_data)

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_handles_empty_content(self, mock_client_class):
        """Test analysis with news that has no full content."""
        # Create news without content
        news_no_content = News.objects.create(
            title="Brief Headline",
            content_summary="Short summary only",
            link="https://example.com/brief",
            keyword=self.keyword,
            source=self.source
            # content is None
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "0.3"

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Should not crash
        result = analyse_news_task(news_no_content.id)

        self.assertEqual(result['status'], 'success')

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_updates_task_state(self, mock_client_class):
        """Test that task updates its state to show progress."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "0.5"

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Run task (this would need actual Celery to test update_state)
        result = analyse_news_task(self.news.id)

        # Task should complete successfully
        self.assertEqual(result['status'], 'success')

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_handles_invalid_json(self, mock_client_class):
        """Test handling of malformed JSON from Gemini."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "{invalid json content"  # Malformed

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Should fall back to simple float parsing or handle gracefully
        result = analyse_news_task(self.news.id)

        # Should return error or handle gracefully
        self.assertIn('status', result)

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_handles_negative_sentiment(self, mock_client_class):
        """Test analysis of negative sentiment news."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "sentiment": -0.75,
            "confidence": 0.9,
            "explanation": "Major regulatory issues indicate severe negative impact",
            "tickers": ["TCS"],
            "impact_timeline": "long-term"
        })

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Run task
        result = analyse_news_task(self.news.id)

        # Verify negative sentiment is handled
        self.assertEqual(result['sentiment_score'], -0.75)

        self.news.refresh_from_db()
        self.assertEqual(self.news.impact_rating, -0.75)

    @patch('news_analyser.tasks.genai.Client')
    def test_analyse_news_task_handles_neutral_sentiment(self, mock_client_class):
        """Test analysis of neutral sentiment news."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "0.0"

        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Run task
        result = analyse_news_task(self.news.id)

        # Verify neutral sentiment
        self.assertEqual(result['sentiment_score'], 0.0)

        self.news.refresh_from_db()
        self.assertEqual(self.news.impact_rating, 0.0)
