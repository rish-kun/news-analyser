import feedparser
import requests
import requests_cache
from bs4 import BeautifulSoup
from trafilatura import fetch_url, extract
from fuzzywuzzy import fuzz
import logging
from playwright.sync_api import sync_playwright
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Caching ---
requests_cache.install_cache('news_cache', backend='sqlite', expire_after=1800)

# --- Sources ---
SOURCES = {
    'rss': {
        'Economic Times': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
        'Mint': 'https://www.livemint.com/rss/markets',
        'Financial Express': 'https://www.financialexpress.com/market/feed/',
        'The Hindu Business Line': 'https://www.thehindubusinessline.com/markets/feeder/default.rss',
        'Moneycontrol': 'https://www.moneycontrol.com/rss/marketreports.xml',
    },
    'web': {
        'BSE India': 'https://www.bseindia.com/corporates/ann.html',
        'NSE India': 'https://www.nseindia.com/companies-listing/corporate-filings-announcements',
        'CNBC TV18': 'https://www.cnbctv18.com/market/',
        'Zerodha Pulse': 'https://pulse.zerodha.com/',
        'Angel One': 'https://www.angelone.in/share-market-today'
    }
}

class NewsScraper:
    def __init__(self, keywords):
        self.keywords = keywords
        self.results = []

    def fetch_rss(self, url):
        """Fetches and parses an RSS feed."""
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                self.process_entry(entry)
        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")

    def process_entry(self, entry):
        """Processes a single news entry from an RSS feed."""
        title = entry.title
        summary = entry.summary if 'summary' in entry else ''
        link = entry.link

        if self.is_relevant(title + " " + summary):
            self.results.append({
                'title': title,
                'summary': summary,
                'link': link,
                'source': 'RSS'
            })

    def _stem(self, word):
        """A simple stemmer."""
        word = word.lower()
        if word.endswith('ing'):
            return word[:-3]
        if word.endswith('s'):
            return word[:-1]
        if word.endswith('ed'):
            return word[:-2]
        return word

    def is_relevant(self, text):
        """Checks if the text is relevant to any of the keywords using fuzzy matching and stemming."""
        text_stemmed = " ".join([self._stem(word) for word in text.split()])
        for keyword in self.keywords:
            keyword_stemmed = self._stem(keyword)
            if fuzz.partial_ratio(keyword_stemmed, text_stemmed) > 80: # Threshold can be adjusted
                return True
        return False

    def fetch_web_bse(self, url):
        """Fetches and parses the BSE India announcements page."""
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the table with the announcements
            announcement_table = soup.find('table', class_='mGrid')

            if announcement_table:
                for row in announcement_table.find_all('tr')[1:]: # Skip header row
                    cols = row.find_all('td')
                    if len(cols) > 2:
                        company_info = cols[1].text.strip()
                        title = cols[2].text.strip()

                        # Extracting link to the announcement PDF
                        link_tag = cols[2].find('a')
                        if link_tag and link_tag.get('href'):
                            pdf_link = "https://www.bseindia.com" + link_tag.get('href')

                            # Check for relevance
                            if self.is_relevant(title + " " + company_info):
                                # Extract content from PDF
                                downloaded = fetch_url(pdf_link)
                                content = extract(downloaded)

                                self.results.append({
                                    'title': title,
                                    'summary': content[:500] if content else title, # take first 500 chars as summary
                                    'link': pdf_link,
                                    'source': 'BSE India'
                                })
        except Exception as e:
            logger.error(f"Error fetching BSE India announcements: {e}")


    def fetch_web_nse(self, url):
        """Fetches and parses the NSE India announcements page using Playwright."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url, wait_until='networkidle')

                # Wait for the table to load
                page.wait_for_selector('#announcements-data', timeout=60000)

                soup = BeautifulSoup(page.content(), 'html.parser')

                rows = soup.select('#announcements-data tr')

                for row in rows:
                    cols = row.select('td')
                    if len(cols) > 2:
                        symbol = cols[0].text.strip()
                        title = cols[2].text.strip()

                        if self.is_relevant(title + " " + symbol):
                            self.results.append({
                                'title': title,
                                'summary': title,
                                'link': "https://www.nseindia.com" + cols[2].find('a')['href'],
                                'source': 'NSE India'
                            })
                browser.close()
        except Exception as e:
            logger.error(f"Error fetching NSE India announcements: {e}")

    def fetch_generic_web(self, url, article_link_selector, source_name):
        """Fetches and parses a generic news website."""
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            for link in soup.select(article_link_selector):
                article_url = link.get('href')
                if not article_url.startswith('http'):
                    base_url = '/'.join(url.split('/')[:3])
                    article_url = base_url + article_url

                downloaded = fetch_url(article_url)
                if downloaded:
                    content = extract(downloaded, include_comments=False, include_tables=False)
                    title = extract(downloaded, include_comments=False, include_tables=False, output_format='json', with_metadata=True)
                    if title:
                        title = json.loads(title).get('title', '')
                    else:
                        title = ""

                    if self.is_relevant(title + " " + content):
                        self.results.append({
                            'title': title,
                            'summary': content[:500] if content else title,
                            'link': article_url,
                            'source': source_name
                        })
        except Exception as e:
            logger.error(f"Error fetching generic web source {source_name}: {e}")

    def run(self):
        """Runs the scraper."""
        # Fetch RSS feeds
        for name, url in SOURCES['rss'].items():
            logger.info(f"Fetching RSS feed: {name}")
            self.fetch_rss(url)

        # Fetch Web sources
        self.fetch_web_bse(SOURCES['web']['BSE India'])
        self.fetch_web_nse(SOURCES['web']['NSE India'])
        self.fetch_generic_web(SOURCES['web']['CNBC TV18'], 'a.m-article-card__link', 'CNBC TV18')
        self.fetch_generic_web(SOURCES['web']['Zerodha Pulse'], 'div.item a.link', 'Zerodha Pulse')
        self.fetch_generic_web(SOURCES['web']['Angel One'], 'div.news-card a', 'Angel One')

        return self.results

if __name__ == '__main__':
    keywords = ['Reliance', 'TCS', 'Infosys']
    scraper = NewsScraper(keywords)
    articles = scraper.run()
    for article in articles:
        print(article)
