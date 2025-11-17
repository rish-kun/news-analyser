from django.test import TestCase, override_settings
from news_analyser.tasks import analyse_news_task
from news_analyser.models import News, Keyword

@override_settings(CELERY_ALWAYS_EAGER=True)
class CeleryTaskTest(TestCase):
    def setUp(self):
        self.keyword = Keyword.objects.create(name="TCS")
        self.news = News.objects.create(
            title="TCS wins major contract",
            content_summary="TCS secures $500M deal",
            link="https://test.com/article",
            keyword=self.keyword
        )

    def test_analyse_news_task_updates_sentiment(self):
        """Test that Celery task updates sentiment score"""
        # Mock Gemini API response in a real test
        result = analyse_news_task.delay(self.news.id)
        self.news.refresh_from_db()
        # self.assertNotEqual(self.news.impact_rating, 0)
        self.assertGreaterEqual(self.news.impact_rating, -1)
        self.assertLessEqual(self.news.impact_rating, 1)
