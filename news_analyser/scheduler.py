import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from .tasks import scrape_and_store_news

logger = logging.getLogger(__name__)

def start():
    """
    Starts the scheduler.
    """
    if settings.DEBUG:
        # Don't run scheduler in debug mode
        return

    scheduler = BackgroundScheduler()
    scheduler.add_job(scrape_and_store_news, 'interval', minutes=30)
    scheduler.start()
    logger.info("Scheduler started.")
