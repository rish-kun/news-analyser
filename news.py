import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
load_dotenv()




#? newsapi.org
newsapi_org_api_key = os.getenv('NEWSAPI_ORG_API_KEY')
headers = {
    "Authorization":newsapi_org_api_key,
}
def get_country_news(country="india"):
    from_date = (datetime.now()-timedelta(days=29)).strftime("%Y-%m-%d")
    top_headlines = f"https://newsapi.org/v2/everything"
    qs={
        "from":from_date,
        "sortBy":"publishedAt",
        "q":country,
        "language":"en",
    }
    req = requests.get(top_headlines, params=qs, headers=headers)
    print(json.dumps(req.json(), indent=2))



def get_top_headlines(country="in", sources="financial-post"):
    top_headlines = f"https://newsapi.org/v2/top-headlines"
    qs = {
        "language":"en",
        "sources":sources,

    }
    req = requests.get(top_headlines, params=qs, headers=headers)
    print(json.dumps(req.json(), indent=2))



def get_sources():
    url ="https://newsapi.org/v2/top-headlines/sources"
    req = requests.get(url, headers=headers)
    js = req.json()
    sources={}
    for s in js["sources"]:
        sources[s["id"]] = s["name"]
    print(sources)
    return sources

if __name__=="__main__":
    get_top_headlines()