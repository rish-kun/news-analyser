from django.test import TestCase
from django.contrib.auth.models import User
from news_analyser.models import News, Keyword, Stock, UserProfile

class NewsModelTest(TestCase):
    def setUp(self):
        self.keyword = Keyword.objects.create(name="RELIANCE")
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.user_profile = UserProfile.objects.create(user=self.user)

    def test_parse_news_creates_new_article(self):
        """Test that parse_news creates a new News object"""
        news_data = {
            'title': 'Reliance Q3 Results',
            'summary': 'Reliance reports strong earnings',
            'link': 'https://economictimes.com/article/123',
            'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
        }
        news = News.parse_news(news_data, self.keyword)
        self.assertIsNotNone(news)
        self.assertEqual(news.title, 'Reliance Q3 Results')
        self.assertEqual(news.keyword, self.keyword)
        self.assertEqual(News.objects.count(), 1)

    def test_parse_news_does_not_duplicate(self):
        """Test that parse_news doesn't create duplicates"""
        news_data = {
            'title': 'Reliance Q3 Results',
            'summary': 'Reliance reports strong earnings',
            'link': 'https://economictimes.com/article/123',
            'published': 'Thu, 15 Nov 2025 10:00:00 GMT'
        }
        news1 = News.parse_news(news_data, self.keyword)
        news2 = News.parse_news(news_data, self.keyword)
        self.assertEqual(news1.id, news2.id)
        self.assertEqual(News.objects.count(), 1)
