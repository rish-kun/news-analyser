"""
RSS Feed Parser for Indian Financial News Sources.

This module handles fetching and parsing RSS feeds from various Indian
news sources including Times of India, Economic Times, The Hindu, MoneyControl,
Business Standard, and LiveMint.
"""

import feedparser
import logging
from typing import Dict, List
from .exceptions import RSSFeedError

logger = logging.getLogger(__name__)

# Times of India RSS feeds
toi_feeds = {
    "recent": "https://timesofindia.indiatimes.com/rssfeedmostrecent.cms",
    "india": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "world": "http://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
    "business": "http://timesofindia.indiatimes.com/rssfeeds/1898055.cms",
    "tech": "http://timesofindia.indiatimes.com/rssfeeds/66949542.cms",
}

# Economic Times RSS feeds
et_feeds = {
    "top_stories": "https://cfo.economictimes.indiatimes.com/rss/topstories",
    "recent": "https://cfo.economictimes.indiatimes.com/rss/recentstories",
    "tax_legal_accounting": "https://cfo.economictimes.indiatimes.com/rss/tax-legal-accounting",
    "corp_finance": "https://cfo.economictimes.indiatimes.com/rss/corporate-finance",
    "economy": "https://cfo.economictimes.indiatimes.com/rss/economy",
    "govt_risk": "https://cfo.economictimes.indiatimes.com/rss/governance-risk-compliance",
    "markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "stocks": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
}

# The Hindu RSS feeds
the_hindu_feeds = {
    "economy": "https://www.thehindu.com/business/Economy/feeder/default.rss",
    "markets": "https://www.thehindu.com/business/markets/feeder/default.rss",
    "budget": "https://www.thehindu.com/business/budget/feeder/default.rss",
    "agri_business": "https://www.thehindu.com/business/agri-business/feeder/default.rss",
    "industry": "https://www.thehindu.com/business/Industry/feeder/default.rss",
}

# MoneyControl RSS feeds
moneycontrol_feeds = {
    "news": "https://www.moneycontrol.com/rss/latestnews.xml",
    "markets": "https://www.moneycontrol.com/rss/marketreports.xml",
    "results": "https://www.moneycontrol.com/rss/results.xml",
    "ipo": "https://www.moneycontrol.com/rss/ipo.xml",
}

# Business Standard RSS feeds
business_standard_feeds = {
    "companies": "https://www.business-standard.com/rss/companies-101.rss",
    "markets": "https://www.business-standard.com/rss/markets-102.rss",
    "finance": "https://www.business-standard.com/rss/finance-103.rss",
    "economy": "https://www.business-standard.com/rss/economy-policy-104.rss",
}

# LiveMint RSS feeds
livemint_feeds = {
    "news": "https://www.livemint.com/rss/news",
    "markets": "https://www.livemint.com/rss/markets",
    "companies": "https://www.livemint.com/rss/companies",
    "money": "https://www.livemint.com/rss/money",
}

# CNBC TV18 RSS feeds
cnbc_feeds = {
    "market": "https://www.cnbctv18.com/rss/market.xml",
    "business": "https://www.cnbctv18.com/rss/business.xml",
}


def check_keywords(keywords: List[str], max_per_feed: int = 50) -> Dict[str, List]:
    """
    Search for keywords across all configured RSS feeds.

    Args:
        keywords (List[str]): List of keywords/stock symbols to search for
        max_per_feed (int): Maximum number of entries to check per feed (default: 50)

    Returns:
        Dict[str, List]: Dictionary mapping keywords to matching news entries

    Raises:
        RSSFeedError: If all feeds fail to parse
    """
    logger.info(f"Starting RSS search for keywords: {keywords}")

    e_s = {}  # dict of format "kwd":["entry", "entry", "entry"]
    import concurrent.futures

    feeds = (
        list(the_hindu_feeds.values())
        + list(et_feeds.values())
        + list(toi_feeds.values())
        + list(moneycontrol_feeds.values())
        + list(business_standard_feeds.values())
        + list(livemint_feeds.values())
        + list(cnbc_feeds.values())
    )

    successful_feeds = 0
    failed_feeds = 0

    def fetch_and_process_feed(feed_url):
        local_results = {}
        try:
            logger.debug(f"Fetching feed: {feed_url}")
            parsed_feed = feedparser.parse(feed_url)

            # Check if feed was successfully parsed
            if parsed_feed.bozo:
                logger.warning(
                    f"Feed parsing warning for {feed_url}: {parsed_feed.bozo_exception}"
                )

            if not hasattr(parsed_feed, 'entries') or not parsed_feed.entries:
                logger.warning(f"No entries found in feed: {feed_url}")
                return False, local_results

            # Limit entries to process
            entries_to_process = parsed_feed.entries[:max_per_feed]
            logger.debug(f"Processing {len(entries_to_process)} entries from {feed_url}")

            for entry in entries_to_process:
                try:
                    # Safely get title and summary
                    title = getattr(entry, 'title', '')
                    summary = getattr(entry, 'summary', '')

                    # Search for keywords in title and summary
                    for keyword in keywords:
                        keyword_lower = keyword.lower()
                        title_lower = title.lower()
                        summary_lower = summary.lower()

                        if keyword_lower in title_lower or keyword_lower in summary_lower:
                            logger.debug(f"Keyword '{keyword}' found in: {title[:50]}...")

                            # Ensure entry has required fields
                            if not hasattr(entry, 'link'):
                                logger.warning(f"Entry missing link field: {title}")
                                continue

                            # Add to results
                            if keyword not in local_results:
                                local_results[keyword] = []

                            # Avoid duplicates
                            if entry not in local_results[keyword]:
                                local_results[keyword].append(entry)

                except Exception as e:
                    logger.error(f"Error processing entry: {e}", exc_info=True)
                    continue
            
            return True, local_results

        except Exception as e:
            logger.error(f"Failed to fetch/parse feed {feed_url}: {e}", exc_info=True)
            return False, local_results

    # Use ThreadPoolExecutor to fetch feeds in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_and_process_feed, url): url for url in feeds}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                success, results = future.result()
                if success:
                    successful_feeds += 1
                    # Merge results
                    for kw, entries in results.items():
                        if kw not in e_s:
                            e_s[kw] = []
                        e_s[kw].extend(entries)
                else:
                    failed_feeds += 1
            except Exception as e:
                logger.error(f"Feed processing generated an exception for {url}: {e}")
                failed_feeds += 1

    logger.info(
        f"RSS search complete. Successful feeds: {successful_feeds}, "
        f"Failed feeds: {failed_feeds}, Keywords with results: {len(e_s)}"
    )

    # If all feeds failed, raise an error
    if successful_feeds == 0:
        raise RSSFeedError("All RSS feeds failed to fetch or parse")

    return e_s


def get_feed_list() -> List[str]:
    """
    Get a list of all configured RSS feed URLs.

    Returns:
        List[str]: All RSS feed URLs
    """
    return (
        list(the_hindu_feeds.values())
        + list(et_feeds.values())
        + list(toi_feeds.values())
        + list(moneycontrol_feeds.values())
        + list(business_standard_feeds.values())
        + list(livemint_feeds.values())
        + list(cnbc_feeds.values())
    )
