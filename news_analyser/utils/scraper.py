# Standard library imports
import logging

# Third-party imports
import requests
from bs4 import BeautifulSoup
from newspaper import Article, ArticleException

# Local application imports
from ..exceptions import ContentExtractionError

# Configure logging
logger = logging.getLogger(__name__)

async def get_news(url):
    """
    Asynchronously fetches and extracts the main content of a news article.

    Uses newspaper3k as the primary extraction tool and falls back to
    BeautifulSoup for basic extraction if newspaper3k fails.

    Args:
        url (str): The URL of the news article to scrape.

    Returns:
        str: The extracted content of the article.

    Raises:
        ContentExtractionError: If content extraction fails for any reason.
    """
    try:
        # Use newspaper3k for intelligent content extraction
        article = Article(url)
        article.download()
        article.parse()

        if article.text:
            return article.text
        else:
            # Fallback to BeautifulSoup for basic extraction
            logger.warning(f"Newspaper3k failed for {url}, falling back to BeautifulSoup.")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            # A simple heuristic: find the largest <p> tags
            paragraphs = soup.find_all('p')

            if not paragraphs:
                raise ContentExtractionError("No content found with BeautifulSoup fallback.")

            return "\n".join([p.get_text() for p in paragraphs])

    except ArticleException as e:
        logger.error(f"Article extraction failed with newspaper3k for URL: {url} - {e}")
        raise ContentExtractionError(f"Newspaper3k could not process the article.") from e
    except requests.RequestException as e:
        logger.error(f"Network error while fetching URL: {url} - {e}")
        raise ContentExtractionError("A network error occurred.") from e
    except Exception as e:
        logger.critical(f"An unexpected error occurred during content extraction for {url}: {e}", exc_info=True)
        raise ContentExtractionError("An unexpected error occurred.") from e
