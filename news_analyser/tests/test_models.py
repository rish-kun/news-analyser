"""
Unit tests for News Analyser models.

This module tests all model methods, relationships, and business logic.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from news_analyser.models import (
    News, Keyword, Stock, Sector, Source, UserProfile
)


class KeywordModelTest(TestCase):
    """Test cases for the Keyword model."""

    def setUp(self):
        """Set up test data."""
        self.keyword = Keyword.objects.create(name="RELIANCE")

    def test_keyword_creation(self):
        """Test that a keyword can be created with required fields."""
        self.assertIsNotNone(self.keyword.id)
        self.assertEqual(self.keyword.name, "RELIANCE")
        self.assertIsNotNone(self.keyword.create_date)

    def test_keyword_str_representation(self):
        """Test the string representation of a keyword."""
        self.assertEqual(str(self.keyword), "RELIANCE")

    def test_keyword_get_news(self):
        """Test retrieving news associated with a keyword."""
        # Create a news item
        source = Source.objects.create(
            id_name="ET",
            name="Economic Times",
            url="https://economictimes.indiatimes.com"
        )
        news = News.objects.create(
            title="Reliance Q3 Results",
            content_summary="Strong earnings reported",
            link="https://example.com/article1",
            keyword=self.keyword,
            source=source
        )

        news_dict = self.keyword.get_news()
        self.assertIn(self.keyword, news_dict)
        self.assertEqual(news_dict[self.keyword].count(), 1)

    def test_keyword_ordering(self):
        """Test that keywords are ordered by create_date descending."""
        kw1 = Keyword.objects.create(name="TCS")
        kw2 = Keyword.objects.create(name="INFY")

        keywords = Keyword.objects.all()
        self.assertEqual(keywords[0], kw2)  # Most recent first


class SourceModelTest(TestCase):
    """Test cases for the Source model."""

    def setUp(self):
        """Set up test data."""
        self.source = Source.objects.create(
            id_name="ET",
            name="Economic Times",
            url="https://economictimes.indiatimes.com"
        )

    def test_source_creation(self):
        """Test that a source can be created."""
        self.assertIsNotNone(self.source.id)
        self.assertEqual(self.source.id_name, "ET")
        self.assertEqual(self.source.name, "Economic Times")

    def test_source_str_representation(self):
        """Test the string representation of a source."""
        self.assertEqual(str(self.source), "Economic Times")


class NewsModelTest(TestCase):
    """Test cases for the News model."""

    def setUp(self):
        """Set up test data."""
        self.keyword = Keyword.objects.create(name="RELIANCE")
        self.source = Source.objects.create(
            id_name="ET",
            name="Economic Times",
            url="https://economictimes.indiatimes.com"
        )

    def test_news_creation(self):
        """Test that a news item can be created."""
        news = News.objects.create(
            title="Reliance Q3 Results",
            content_summary="Strong earnings",
            link="https://example.com/article1",
            keyword=self.keyword,
            source=self.source
        )

        self.assertIsNotNone(news.id)
        self.assertEqual(news.title, "Reliance Q3 Results")
        self.assertEqual(news.impact_rating, 0)  # Default value

    def test_news_unique_link_constraint(self):
        """Test that news links must be unique."""
        News.objects.create(
            title="Article 1",
            content_summary="Summary 1",
            link="https://example.com/unique",
            keyword=self.keyword,
            source=self.source
        )

        # Try to create another news with same link
        news2 = News.objects.create(
            title="Article 2",
            content_summary="Summary 2",
            link="https://example.com/different",
            keyword=self.keyword,
            source=self.source
        )

        # Should work for different links
        self.assertEqual(News.objects.count(), 2)

    def test_news_parse_news_creates_new(self):
        """Test that parse_news creates a new News object."""
        news_data = {
            'title': 'Reliance Announces Merger',
            'summary': 'Major business development',
            'link': 'https://economictimes.indiatimes.com/article/123',
            'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
        }

        news = News.parse_news(news_data, self.keyword)

        self.assertIsNotNone(news)
        self.assertEqual(news.title, 'Reliance Announces Merger')
        self.assertEqual(news.keyword, self.keyword)
        self.assertIsNotNone(news.source)

    def test_news_parse_news_does_not_duplicate(self):
        """Test that parse_news doesn't create duplicates for same link."""
        news_data = {
            'title': 'Article Title',
            'summary': 'Article summary',
            'link': 'https://example.com/article',
            'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
        }

        news1 = News.parse_news(news_data, self.keyword)
        news2 = News.parse_news(news_data, self.keyword)

        self.assertEqual(news1.id, news2.id)
        self.assertEqual(News.objects.count(), 1)

    def test_news_source_detection_economic_times(self):
        """Test automatic source detection for Economic Times."""
        news_data = {
            'title': 'ET Article',
            'summary': 'Summary',
            'link': 'https://economictimes.indiatimes.com/markets/article',
            'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
        }

        news = News.parse_news(news_data, self.keyword)
        self.assertEqual(news.source.id_name, "ET")

    def test_news_source_detection_times_of_india(self):
        """Test automatic source detection for Times of India."""
        news_data = {
            'title': 'TOI Article',
            'summary': 'Summary',
            'link': 'https://timesofindia.indiatimes.com/business/article',
            'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
        }

        news = News.parse_news(news_data, self.keyword)
        self.assertEqual(news.source.id_name, "TOI")

    def test_news_source_detection_moneycontrol(self):
        """Test automatic source detection for MoneyControl."""
        news_data = {
            'title': 'MC Article',
            'summary': 'Summary',
            'link': 'https://www.moneycontrol.com/news/business/article',
            'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
        }

        news = News.parse_news(news_data, self.keyword)
        self.assertEqual(news.source.id_name, "MC")

    def test_news_enhanced_sentiment_fields(self):
        """Test that enhanced sentiment fields can be set."""
        news = News.objects.create(
            title="Test Article",
            content_summary="Summary",
            link="https://example.com/test",
            keyword=self.keyword,
            source=self.source,
            impact_rating=0.75,
            sentiment_confidence=0.85,
            sentiment_explanation="Strong positive earnings indicate good market performance",
            mentioned_tickers=["RELIANCE", "TCS"],
            raw_gemini_response={"sentiment": 0.75, "confidence": 0.85}
        )

        self.assertEqual(news.sentiment_confidence, 0.85)
        self.assertIsNotNone(news.sentiment_explanation)
        self.assertEqual(len(news.mentioned_tickers), 2)
        self.assertIn("RELIANCE", news.mentioned_tickers)

    def test_news_ordering(self):
        """Test that news are ordered by date descending."""
        yesterday = timezone.now() - timedelta(days=1)
        today = timezone.now()

        news1 = News.objects.create(
            title="Old News",
            content_summary="Summary",
            link="https://example.com/old",
            keyword=self.keyword,
            source=self.source,
            date=yesterday
        )

        news2 = News.objects.create(
            title="New News",
            content_summary="Summary",
            link="https://example.com/new",
            keyword=self.keyword,
            source=self.source,
            date=today
        )

        news_list = News.objects.all()
        self.assertEqual(news_list[0], news2)  # Most recent first


class SectorModelTest(TestCase):
    """Test cases for the Sector model."""

    def test_sector_creation(self):
        """Test that a sector can be created."""
        sector = Sector.objects.create(
            name="Information Technology",
            search_fields="IT, software, tech"
        )

        self.assertIsNotNone(sector.id)
        self.assertEqual(sector.name, "Information Technology")

    def test_sector_str_representation(self):
        """Test the string representation of a sector."""
        sector = Sector.objects.create(name="Banking")
        self.assertEqual(str(sector), "Banking")


class StockModelTest(TestCase):
    """Test cases for the Stock model."""

    def setUp(self):
        """Set up test data."""
        self.sector = Sector.objects.create(name="IT")

    def test_stock_creation(self):
        """Test that a stock can be created."""
        stock = Stock.objects.create(
            name="Tata Consultancy Services",
            symbol="TCS",
            sector=self.sector
        )

        self.assertIsNotNone(stock.id)
        self.assertEqual(stock.symbol, "TCS")
        self.assertEqual(stock.sector, self.sector)

    def test_stock_str_representation(self):
        """Test the string representation of a stock."""
        stock = Stock.objects.create(
            name="Tata Consultancy Services",
            symbol="TCS",
            sector=self.sector
        )

        self.assertEqual(str(stock), "TCS - Tata Consultancy Services")


class UserProfileModelTest(TestCase):
    """Test cases for the UserProfile model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_user_profile_creation(self):
        """Test that a user profile can be created."""
        profile = UserProfile.objects.create(user=self.user)

        self.assertIsNotNone(profile.id)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.preferences, {})

    def test_user_profile_str_representation(self):
        """Test the string representation of a user profile."""
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(str(profile), "Profile of testuser")

    def test_user_profile_stocks_relationship(self):
        """Test the many-to-many relationship with stocks."""
        profile = UserProfile.objects.create(user=self.user)
        sector = Sector.objects.create(name="IT")
        stock1 = Stock.objects.create(name="TCS", symbol="TCS", sector=sector)
        stock2 = Stock.objects.create(name="Infosys", symbol="INFY", sector=sector)

        profile.stocks.add(stock1, stock2)

        self.assertEqual(profile.stocks.count(), 2)
        self.assertIn(stock1, profile.stocks.all())

    def test_user_profile_searches_relationship(self):
        """Test the many-to-many relationship with keywords."""
        profile = UserProfile.objects.create(user=self.user)
        kw1 = Keyword.objects.create(name="RELIANCE")
        kw2 = Keyword.objects.create(name="TCS")

        profile.searches.add(kw1, kw2)

        self.assertEqual(profile.searches.count(), 2)
        self.assertIn(kw1, profile.searches.all())
