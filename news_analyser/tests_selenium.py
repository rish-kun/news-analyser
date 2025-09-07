import time
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .models import Keyword

class NewsAnalyserSeleniumTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selenium = webdriver.Chrome()
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_search_and_loading(self):
        # Create a user
        User.objects.create_user('testuser', 'test@example.com', 'testpassword')

        # Login
        self.selenium.get(f'{self.live_server_url}/login/')
        self.selenium.find_element(By.NAME, 'username').send_keys('testuser')
        self.selenium.find_element(By.NAME, 'password').send_keys('testpassword')
        self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        # Wait for redirect to search page
        WebDriverWait(self.selenium, 10).until(
            EC.url_contains('/search/')
        )

        # Search for a new keyword
        self.selenium.find_element(By.NAME, 'keyword').send_keys('Microsoft')
        self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()

        # Wait for redirect to loading page
        WebDriverWait(self.selenium, 10).until(
            EC.url_contains('/loading/')
        )

        # Wait for the result link to appear
        try:
            result_link = WebDriverWait(self.selenium, 300).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#result-link a"))
            )
        except Exception as e:
            print(f"Current URL: {self.selenium.current_url}")
            raise e

        # Go to the results page
        result_link.click()

        # Verify that we are on the results page and the content is correct
        WebDriverWait(self.selenium, 10).until(
            EC.url_contains('/search/')
        )
        self.assertTrue(
            "Microsoft" in self.selenium.page_source
        )
