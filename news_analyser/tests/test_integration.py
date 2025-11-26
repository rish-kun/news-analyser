"""
Integration tests for News Analyser application.

This module tests end-to-end workflows combining multiple components.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import json

from news_analyser.models import (
    News, Keyword, Stock, Sector, Source, UserProfile
)


class UserWorkflowIntegrationTest(TestCase):
    """Test complete user workflows from registration to news analysis."""

    def setUp(self):
        """Set up test client and data."""
        self.client = Client()
        # Create some test stocks
        self.sector = Sector.objects.create(name="IT")
        self.stock1 = Stock.objects.create(
            name="Tata Consultancy Services",
            symbol="TCS",
            sector=self.sector
        )
        self.stock2 = Stock.objects.create(
            name="Infosys",
            symbol="INFY",
            sector=self.sector
        )

    def test_user_registration_creates_profile(self):
        """Test that user registration automatically creates a profile."""
        response = self.client.post(reverse('news_analyser:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123'
        })

        # Verify user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())

        # Verify profile was created
        user = User.objects.get(username='newuser')
        self.assertTrue(hasattr(user, 'profile'))

    @patch('news_analyser.rss.feedparser.parse')
    def test_complete_search_and_analysis_flow(self, mock_parse):
        """Test complete flow: login -> search -> view results -> view details."""
        # 1. Create and login user
        user = User.objects.create_user('testuser', 'test@example.com', 'pass123')
        UserProfile.objects.create(user=user)
        self.client.login(username='testuser', password='pass123')

        # 2. Mock RSS feed response
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                'title': 'RELIANCE Q3 Results Beat Expectations',
                'summary': 'Reliance Industries reports strong quarterly earnings',
                'link': 'https://economictimes.indiatimes.com/reliance-q3',
                'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
            }
        ]
        mock_parse.return_value = mock_feed

        # 3. Perform search
        response = self.client.post(reverse('news_analyser:search'), {
            'search_type': 'keyword',
            'keyword': 'RELIANCE'
        })

        # Should redirect to results
        self.assertEqual(response.status_code, 302)

        # 4. Verify news was created
        self.assertTrue(News.objects.filter(title__icontains='RELIANCE').exists())

        # 5. Verify keyword was created and associated with user
        self.assertTrue(Keyword.objects.filter(name='RELIANCE').exists())
        keyword = Keyword.objects.get(name='RELIANCE')
        self.assertIn(keyword, user.profile.searches.all())

        # 6. View results page
        news = News.objects.first()
        response = self.client.get(
            reverse('news_analyser:search_results', args=[keyword.id])
        )
        self.assertEqual(response.status_code, 200)

    @patch('news_analyser.tasks.genai.Client')
    @patch('news_analyser.rss.feedparser.parse')
    def test_news_fetch_and_sentiment_analysis(self, mock_parse, mock_genai):
        """Test fetching news and running sentiment analysis."""
        # Setup user
        user = User.objects.create_user('investor', 'test@test.com', 'pass123')
        UserProfile.objects.create(user=user)
        self.client.login(username='investor', password='pass123')

        # Mock RSS feed
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                'title': 'TCS Wins Major Contract',
                'summary': 'TCS secures $500M deal',
                'link': 'https://example.com/tcs-news',
                'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
            }
        ]
        mock_parse.return_value = mock_feed

        # Mock Gemini API
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "sentiment": 0.75,
            "confidence": 0.85,
            "explanation": "Major contract win",
            "tickers": ["TCS"],
            "impact_timeline": "short-term"
        })
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.return_value = mock_client

        # Search for TCS
        self.client.post(reverse('news_analyser:search'), {
            'search_type': 'keyword',
            'keyword': 'TCS'
        })

        # Verify news was created
        news = News.objects.first()
        self.assertIsNotNone(news)
        self.assertIn('TCS', news.title)

        # Manually trigger analysis (in real app, Celery would do this)
        from news_analyser.tasks import analyse_news_task
        result = analyse_news_task(news.id)

        # Verify analysis completed
        news.refresh_from_db()
        self.assertNotEqual(news.impact_rating, 0)

    def test_user_can_manage_watchlist(self):
        """Test user can add and remove stocks from watchlist."""
        # Create and login user
        user = User.objects.create_user('investor', 'test@example.com', 'pass123')
        profile = UserProfile.objects.create(user=user)
        self.client.login(username='investor', password='pass123')

        # Add stocks to watchlist
        response = self.client.post(reverse('news_analyser:add_stocks'), {
            'stocks': [self.stock1.id, self.stock2.id]
        })

        # Verify stocks were added
        profile.refresh_from_db()
        self.assertEqual(profile.stocks.count(), 2)
        self.assertIn(self.stock1, profile.stocks.all())

    def test_search_requires_authentication(self):
        """Test that search views require authentication."""
        # Try to access search without logging in
        response = self.client.get(reverse('news_analyser:search'))

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_past_searches_displays_user_history(self):
        """Test that past searches page shows user's search history."""
        # Create user with search history
        user = User.objects.create_user('testuser', 'test@example.com', 'pass123')
        profile = UserProfile.objects.create(user=user)

        kw1 = Keyword.objects.create(name="RELIANCE")
        kw2 = Keyword.objects.create(name="TCS")
        profile.searches.add(kw1, kw2)

        self.client.login(username='testuser', password='pass123')

        # Access past searches
        response = self.client.get(reverse('news_analyser:past_searches'))

        # Verify searches are displayed
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RELIANCE")
        self.assertContains(response, "TCS")
