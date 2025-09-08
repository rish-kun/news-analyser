from selenium.webdriver.common.by import By
from .base_page import BasePage

class ResultsPage(BasePage):
    NEWS_ROWS = (By.CSS_SELECTOR, "tbody tr")

    def __init__(self, driver, live_server_url):
        super().__init__(driver, live_server_url)

    def get_news_count(self):
        return len(self.driver.find_elements(*self.NEWS_ROWS))
