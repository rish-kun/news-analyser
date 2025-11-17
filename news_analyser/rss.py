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

livemint_feeds = {
    "companies": "https://www.livemint.com/rss/companies",
    "money": "https://www.livemint.com/rss/money",
    "mutual_funds": "https://www.livemint.com/rss/mutual-funds",
}

moneycontrol_feeds = {
    "business": "https://www.moneycontrol.com/rss/business.xml",
    "stocks": "https://www.moneycontrol.com/rss/stocks.xml",
    "mutual_funds": "https://www.moneycontrol.com/rss/mfnews.xml",
}

business_standard_feeds = {
    "finance": "https://www.business-standard.com/rss/finance-103.rss",
    "markets": "https://www.business-standard.com/rss/markets-106.rss",
    "companies": "https://www.business-standard.com/rss/companies-101.rss",
}

financial_express_feeds = {
    "market": "https://www.financialexpress.com/market/rss",
    "economy": "https://www.financialexpress.com/economy/rss",
    "industry": "https://www.financialexpress.com/industry/rss",
}

india_tv_feeds = {
    "finance": "https://www.indiatvnews.com/rss/finance.xml",
}

# each feed has the following:
# 'summary', 'title', 'link'


def check_keywords(keywords):
    e_s = {}  # dict of format "kwd":["entry", "entry", "entry"]
    feeds = list(the_hindu_feeds.values()) + \
        list(et_feeds.values())+list(toi_feeds.values()) + \
        list(livemint_feeds.values()) + list(moneycontrol_feeds.values()) + \
        list(business_standard_feeds.values()) + \
        list(financial_express_feeds.values()) + list(india_tv_feeds.values())
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
