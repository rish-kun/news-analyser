from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .models import News, Keyword, Source
from .scraper import NewsScraper
from google import genai
import os
from blackbox.settings import GEMINI_API_KEY
from .prompts import news_analysis_prompt
import logging

logger = logging.getLogger(__name__)

@shared_task
def scrape_and_store_news():
    """
    Scrapes news from all sources and stores them in the database.
    """
    logger.info("Starting news scraping task.")
    keywords = list(Keyword.objects.all().values_list('name', flat=True))
    if not keywords:
        logger.warning("No keywords found in the database. Aborting scraping task.")
        return

    scraper = NewsScraper(keywords)
    articles = scraper.run()

    for article in articles:
        # Get or create the source
        source, _ = Source.objects.get_or_create(name=article['source'], defaults={'url': article['link']})

        # Create or update the news item
        news_item, created = News.objects.update_or_create(
            link=article['link'],
            defaults={
                'title': article['title'],
                'content_summary': article['summary'],
                'source': source,
            }
        )

        # Find relevant keywords and add them
        relevant_keywords = []
        for keyword in keywords:
            if scraper.is_relevant(article['title'] + " " + article['summary']):
                kw, _ = Keyword.objects.get_or_create(name=keyword)
                relevant_keywords.append(kw)

        news_item.keywords.add(*relevant_keywords)

        if created:
            # Analyze the news item only if it's new
            analyse_news_task(news_item.id)
            logger.info(f"New article found: {article['title']}")

    logger.info(f"Scraping task finished. Found {len(articles)} relevant articles.")


@shared_task
def analyse_news_task(news_id):
    print("Analysing news item with id:", news_id)
    try:
        news = News.objects.get(id=news_id)
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = news_analysis_prompt.format(
            title=news.title, content_summary=news.content_summary, content=news.content)
        while True:
            try:
                print("news analysis started")
                analysis = client.models.generate_content(
                    model="gemini-2.5-flash-preview-05-20", contents=prompt)
                news.impact_rating = float(analysis.text)
                print("analysis done")
                news.save()
            except genai.errors.ClientError:
                alt_api_key = os.getenv("GEMINI_API_KEY")
                client2 = genai.Client(api_key=alt_api_key)
                analysis = client2.models.generate_content(
                    model="gemini-2.5-flash-preview-05-20", contents=prompt)
                news.impact_rating = float(analysis.text)
                news.save()
            except Exception as e:
                print(e)
                return "Error"
            else:
                break
    except News.DoesNotExist:
        # Handle case where news item is not found
        print(f"News item with id {news_id} not found.")
    except Exception as e:
        # Handle other potential exceptions
        print(f"An error occurred while analyzing news item {news_id}: {e}")
