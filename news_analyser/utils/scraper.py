# scraping the news page to anaylse the news
import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service


def scrape_news(url):
    chrome_driver_path = ""
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(
        chrome_driver_path), options=options)
        


"""
streamlit
langchain
langchain_ollama
selenium
beautifulsoup4
lxml
html5lib
python-dotenv
"""
