from google import genai
from dotenv import load_dotenv
import os
import requests

load_dotenv()

url = "https://economictimes.indiatimes.com/news/international/global-trends/104-tariff-is-trump-pushing-us-china-into-a-thucydidess-trap/articleshow/120122784.cms"
url = "https://www.reuters.com/markets/rates-bonds/india-cenbank-cuts-rates-second-time-us-tariffs-add-growth-risks-changes-stance-2025-04-09/"
resp = requests.get(url)

gemini_api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_api_key)
pg_content = client.models.generate_content(
    model="gemini-2.0-flash", contents=f"Extract the content of the news article from the following html: {resp.text}")
try:
    analysis = client.models.generate_content(
        model="gemini-2.0-flash-thinking-exp-01-21", contents=f"""How much would the following news article impact the stocks in the Indian stock market (based on the following rating system: -1: Severely negative impact.
-0.75: Highly negative impact.
-0.5: Moderately negative impact.
-0.25: Slightly negative impact.
0: No effect.
0.25: Slightly positive impact.
0.5: Moderately positive impact.
0.75: Highly positive impact.
1: Extremely positive impact). Only give the rating as the response and a one line reason nothing else: {pg_content.text}""")
except Exception as e:
    print(e)
    analysis = client.models.generate_content(
        model="gemini-2.0-flash", contents=f"How much would the following news article impact the Indian steel stocks in the stock market (on a scale of - to 1, -1 showing a negative impact, 0 showing no effect,  and 1 being the most positive effect). Only give the rating as the response, nothing else: {pg_content.text}")
    print("gemini flash")

print(analysis.text)
