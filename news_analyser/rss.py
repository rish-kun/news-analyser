import feedparser

toi_feeds = {
    "recent": "https://timesofindia.indiatimes.com/rssfeedmostrecent.cms",
    "india": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "world": "http://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
    "business": "http://timesofindia.indiatimes.com/rssfeeds/1898055.cms",
    "tech": "http://timesofindia.indiatimes.com/rssfeeds/66949542.cms",


}
et_feeds = {
    "top_stories": "https://cfo.economictimes.indiatimes.com/rss/topstories",
    "recent": "https://cfo.economictimes.indiatimes.com/rss/recentstories",
    "tax_legal_accounting": "https://cfo.economictimes.indiatimes.com/rss/tax-legal-accounting",
    "corp_finance": "https://cfo.economictimes.indiatimes.com/rss/corporate-finance",
    "economy": "https://cfo.economictimes.indiatimes.com/rss/economy",
    "govt_risk": "https://cfo.economictimes.indiatimes.com/rss/governance-risk-compliance",

}


the_hindu_feeds = {
    "economy": "https://www.thehindu.com/business/Economy/feeder/default.rss",
    "markets": "https://www.thehindu.com/business/markets/feeder/default.rss",
    "budget": "https://www.thehindu.com/business/budget/feeder/default.rss",
    "agri_business": "https://www.thehindu.com/business/agri-business/feeder/default.rss",
    "industry": "https://www.thehindu.com/business/Industry/feeder/default.rss",

}

# each feed has the following:
# 'summary', 'title', 'link'


def check_keywords(keywords):
    e_s = {}  # dict of format "kwd":["entry", "entry", "entry"]
    feeds = list(the_hindu_feeds.values()) + \
        list(et_feeds.values())+list(toi_feeds.values())
    for feed in feeds:
        for entry in feedparser.parse(feed).entries:
            for keyword in keywords:
                if keyword in entry.title or keyword in entry.summary:
                    e_s[keyword] = [entry] + e_s.get(keyword, [])
                    print("keyword found")
                else:
                    print("not found")
    return e_s

# feeds = list(the_hindu_feeds.values())+ list(et_feeds.values())+list(toi_feeds.values())
# for feed in feeds:
#     for entry in feedparser.parse(feed).entries[:1]:
#         print(entry.title)
#         print(entry.link)
#         print(entry['published'])
#         print("\n\n")
