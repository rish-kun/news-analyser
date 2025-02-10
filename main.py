from news import get_sources
from sheets import update_sources


sources = get_sources()
update_sources(sources)





# import os
# from dotenv import load_dotenv
# import requests
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# from googleapiclient.discovery import build
# import pickle
# from news_api import get_newsapi_articles, get_top_headlines_india

# # Load environment variables
# load_dotenv()

# # API Keys
# NEWSAPI_KEY = os.getenv('NEWSAPI_ORG_API_KEY')
# NEWSDATAHUB_KEY = os.getenv('NEWSDATAHUB_API_KEY')
# print(NEWSAPI_KEY)
# print(NEWSDATAHUB_KEY)
# # Google Sheets API setup





# def get_newsdata_articles():
#     url = 'https://api.newsdatahub.com/v1'  # Correcting back to the right URL

#     headers = {
#         'X-Api-Key': NEWSDATAHUB_KEY,
#         'Accept': 'application/json',
#         'User-Agent': 'Mozilla/5.0 Chrome/83.0.4103.97 Safari/537.36',
#     }

#     params = {
#         'category': 'business',
#         'language': 'en'
#     }

#     try:
#         response = requests.get(url, params=params, headers=headers)
#         data = response.json()
#         if response.status_code != 200:
#             print(f"Error response from NewsData API: {data}")
#             return []
#         print(data)
#         return data.get('results', [])
#     except Exception as e:
#         print(f"Error fetching from NewsData: {e}")
#         return []



# def main():
#     # Get articles from all sources
#     # newsapi_articles = get_newsapi_articles()
#     newsdata_articles = get_newsdata_articles()
#     india_headlines = get_top_headlines_india()

#     # print("Regular news articles count:", len(newsapi_articles))
#     print("NewsData articles count:", len(newsdata_articles))
#     print("India top headlines count:", len(india_headlines))

#     print("India Headlines:")
#     print(india_headlines)
#     print("\nNewsData Articles:")
#     print(newsdata_articles)


# if __name__ == "__main__":
#     main()
