import feedparser
import logging
from ..exceptions import RSSFeedError

logger = logging.getLogger(__name__)

def check_keywords(keywords):
    """
    Checks for keywords in the RSS feeds of various news sources.
    """
    news = {}
    sources = [
        "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://www.thehindu.com/feeder/default.rss",
        "https://www.livemint.com/rss/homepage",
        "https://www.business-standard.com/rss/latest.rss",
        "https://www.cnbctv18.com/rss/cnbctv18-news-enterprise-rss.xml"
    ]

    for keyword in keywords:
        news[keyword] = []
        for source in sources:
            try:
                feed = feedparser.parse(source)
                for entry in feed.entries:
                    if keyword.lower() in entry.title.lower() or keyword.lower() in entry.summary.lower():
                        news[keyword].append({
                            "title": entry.title,
                            "summary": entry.summary,
                            "link": entry.link,
                            "published": entry.get("published", None)
                        })
            except Exception as e:
                logger.error(f"Error parsing RSS feed {source}: {e}", exc_info=True)
                raise RSSFeedError(f"Could not parse RSS feed: {source}") from e
    return news
