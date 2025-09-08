from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from .base_page import BasePage
from .search_page import SearchPage

class LoginPage(BasePage):
    USERNAME_INPUT = (By.ID, "id_username")
    PASSWORD_INPUT = (By.ID, "id_password")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
    SEARCH_HEADER = (By.XPATH, "//h1[normalize-space()='Search News']")

    def __init__(self, driver, live_server_url):
        super().__init__(driver, live_server_url)
        self.navigate("/login/")

    def login(self, username, password):
        self.fill(self.USERNAME_INPUT, username)
        self.fill(self.PASSWORD_INPUT, password)
        pre_submit_url = self.driver.current_url
        self.click(self.SUBMIT_BUTTON)
        self.wait.until(lambda driver: driver.current_url != pre_submit_url)
        self.wait.until(EC.visibility_of_element_located(self.SEARCH_HEADER))
        return SearchPage(self.driver, self.live_server_url)
