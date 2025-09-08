import os
import logging
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from django.contrib.auth.models import User
from .models import UserProfile, Source
from .page_objects.register_page import RegisterPage
from .page_objects.login_page import LoginPage
from unittest.mock import patch
from django.db import transaction

class NewsAnalyserE2ETests(StaticLiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--proxy-server='direct://'")
        options.add_argument("--proxy-bypass-list=*")
        options.add_argument("--enable-logging")
        options.add_argument("--log-level=0")

        cls.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Test server running at: {self.live_server_url}")

        with transaction.atomic():
            Source.objects.create(id_name="ET", name="Economic Times", url="http://economictimes.com")
            Source.objects.create(id_name="TOI", name="Times of India", url="http://timesofindia.com")
            Source.objects.create(id_name="TH", name="The Hindu", url="http://thehindu.com")
            Source.objects.create(id_name="OTHER", name="Other", url="http://other.com")

        self.assertEqual(Source.objects.count(), 4)

    @patch('news_analyser.views.analyse_news_task.delay')
    @patch('news_analyser.views.check_keywords')
    def test_registration_and_search(self, mock_check_keywords, mock_analyse_news_task):
        self.logger.info("Starting registration and search test")
        mock_check_keywords.return_value = {
            'technology': [{'title': 'Test News', 'summary': 'Test Summary', 'link': 'http://example.com/1', 'published': 'Tue, 26 Mar 2024 12:00:00 +0000'}]
        }

        register_page = RegisterPage(self.driver, self.live_server_url)
        search_page = register_page.register("testuser_reg", "test_reg@example.com", "password")
        results_page = search_page.search_by_keyword("technology")
        self.assertEqual(results_page.get_news_count(), 1)
        self.logger.info("Registration and search test passed")


    @patch('news_analyser.views.analyse_news_task.delay')
    @patch('news_analyser.views.check_keywords')
    def test_login_and_search(self, mock_check_keywords, mock_analyse_news_task):
        self.logger.info("Starting login and search test")
        with transaction.atomic():
            user = User.objects.create_user('testuser_login', 'test_login@example.com', 'password')
            UserProfile.objects.create(user=user)

        mock_check_keywords.return_value = {
            'technology': [{'title': 'Test News', 'summary': 'Test Summary', 'link': 'http://example.com/1', 'published': 'Tue, 26 Mar 2024 12:00:00 +0000'}]
        }

        login_page = LoginPage(self.driver, self.live_server_url)
        search_page = login_page.login("testuser_login", "password")
        results_page = search_page.search_by_keyword("technology")
        self.assertEqual(results_page.get_news_count(), 1)
        self.logger.info("Login and search test passed")
