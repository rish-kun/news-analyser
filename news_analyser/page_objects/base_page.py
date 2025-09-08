from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

class BasePage:
    def __init__(self, driver, live_server_url):
        self.driver = driver
        self.live_server_url = live_server_url
        self.wait = WebDriverWait(driver, 20)

    def find_element(self, by_locator):
        return self.wait.until(EC.visibility_of_element_located(by_locator))

    def click(self, by_locator):
        self.wait.until(EC.element_to_be_clickable(by_locator)).click()

    def fill(self, by_locator, text):
        element = self.find_element(by_locator)
        element.clear()
        element.send_keys(text)

    def get_text(self, by_locator):
        return self.find_element(by_locator).text

    def navigate(self, path):
        self.driver.get(self.live_server_url + path)
        self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
