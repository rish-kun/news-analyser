import os
import django
from playwright.async_api import async_playwright
from django.conf import settings
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from asgiref.sync import sync_to_async

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blackbox.settings')
settings.ALLOWED_HOSTS = ['testserver']
settings.ROOT_URLCONF = 'blackbox.urls'
settings.CELERY_ALWAYS_EAGER = True

# Use a local SQLite database for verification
settings.DATABASES['default'] = {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': 'verification.sqlite3',
}
django.setup()

from django.contrib.auth.models import User
from news_analyser.models import UserProfile, Source

@sync_to_async
def setup_test_data():
    call_command('migrate', '--noinput')
    user, created = User.objects.get_or_create(username='testuser')
    if created:
        user.set_password('password')
        user.save()
        UserProfile.objects.create(user=user)

    Source.objects.get_or_create(id_name="ET", name="Economic Times", url="https://economictimes.indiatimes.com/")
    Source.objects.get_or_create(id_name="TOI", name="Times of India", url="https://timesofindia.indiatimes.com/")
    Source.objects.get_or_create(id_name="TH", name="The Hindu", url="https://www.thehindu.com/")
    Source.objects.get_or_create(id_name="OTHER", name="Other", url="https://www.google.com/")

    return user

async def take_screenshots():
    """
    This script logs in, performs a search, and takes screenshots of the key pages.
    """
    # Create a test client
    client = Client()

    # Create a dummy user for the test
    user = await setup_test_data()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 1. Arrange: Go to the login page and take a screenshot.
        response = await sync_to_async(client.get)(reverse('login'))
        await page.set_content(response.content.decode('utf-8'))
        await page.screenshot(path="docs/screenshots/01_login_page.png")

        # 2. Act: Log in.
        await sync_to_async(client.login)(username='testuser', password='password')

        # 3. Arrange: Go to the search page and take a screenshot.
        response = await sync_to_async(client.get)(reverse('news_analyser:search'))
        await page.set_content(response.content.decode('utf-8'))
        await page.screenshot(path="docs/screenshots/02_search_page.png")

        # 4. Act: Perform a search.
        response = await sync_to_async(client.post)(reverse('news_analyser:search'), {'search_type': 'keyword', 'keyword': 'RELIANCE'})

        # 5. Assert: Confirm the results page is loaded and take a screenshot.
        response = await sync_to_async(client.get)(response.url)
        await page.set_content(response.content.decode('utf-8'))
        await page.screenshot(path="docs/screenshots/03_results_page.png")

        await browser.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(take_screenshots())
