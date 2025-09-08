from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from .base_page import BasePage
from .results_page import ResultsPage

class SearchPage(BasePage):
    KEYWORD_INPUT = (By.ID, "keyword")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    RESULTS_HEADER = (By.XPATH, "//h1[contains(text(), 'Search Results')]")


    def __init__(self, driver, live_server_url):
        super().__init__(driver, live_server_url)
        # Don't navigate on init, this page is reached by other actions
        # self.navigate("/")

    def search_by_keyword(self, keyword):
        self.fill(self.KEYWORD_INPUT, keyword)
        pre_submit_url = self.driver.current_url
        self.click(self.SUBMIT_BUTTON)
        self.wait.until(lambda driver: driver.current_url != pre_submit_url)
        self.wait.until(EC.visibility_of_element_located(self.RESULTS_HEADER))
        return ResultsPage(self.driver, self.live_server_url)
