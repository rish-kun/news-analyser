"""
Playwright script to capture screenshots of the News Analyser application.

This script:
1. Sets up test data in the database
2. Launches the application
3. Navigates through key pages
4. Captures screenshots for documentation

Requirements:
- Playwright installed: pip install playwright
- Playwright browsers installed: playwright install chromium
- Django app running or able to start
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project directory to the path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blackbox.settings')

import django
django.setup()

from playwright.async_api import async_playwright
from django.contrib.auth.models import User
from news_analyser.models import (
    Keyword, News, Stock, Sector, Source, UserProfile
)
from django.utils import timezone
import json


# Configuration
SCREENSHOTS_DIR = BASE_DIR / 'screenshots'
BASE_URL = 'http://localhost:8000'
USERNAME = 'testuser'
PASSWORD = 'testpass123'
EMAIL = 'test@example.com'


async def setup_test_data():
    """Create test data for screenshots."""
    print("Setting up test data...")

    # Create test user
    user, created = User.objects.get_or_create(
        username=USERNAME,
        defaults={'email': EMAIL}
    )
    if created:
        user.set_password(PASSWORD)
        user.save()
        print(f"✓ Created test user: {USERNAME}")

    # Create user profile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    print("✓ Created user profile")

    # Create sectors
    it_sector, _ = Sector.objects.get_or_create(
        name="Information Technology",
        defaults={'search_fields': 'IT, software, tech'}
    )
    banking_sector, _ = Sector.objects.get_or_create(
        name="Banking",
        defaults={'search_fields': 'bank, finance, financial'}
    )
    print("✓ Created sectors")

    # Create stocks
    stocks_data = [
        ('Tata Consultancy Services', 'TCS', it_sector),
        ('Infosys', 'INFY', it_sector),
        ('Wipro', 'WIPRO', it_sector),
        ('Reliance Industries', 'RELIANCE', None),
        ('HDFC Bank', 'HDFCBANK', banking_sector),
        ('ICICI Bank', 'ICICIBANK', banking_sector),
    ]

    for name, symbol, sector in stocks_data:
        stock, _ = Stock.objects.get_or_create(
            symbol=symbol,
            defaults={'name': name, 'sector': sector}
        )

    # Add stocks to user's watchlist
    profile.stocks.set(Stock.objects.filter(symbol__in=['TCS', 'RELIANCE', 'HDFCBANK']))
    print("✓ Created stocks and watchlist")

    # Create sources
    sources_data = [
        ('ET', 'Economic Times', 'https://economictimes.indiatimes.com'),
        ('TOI', 'Times of India', 'https://timesofindia.indiatimes.com'),
        ('TH', 'The Hindu', 'https://www.thehindu.com'),
        ('MC', 'MoneyControl', 'https://www.moneycontrol.com'),
    ]

    for id_name, name, url in sources_data:
        Source.objects.get_or_create(
            id_name=id_name,
            defaults={'name': name, 'url': url}
        )
    print("✓ Created news sources")

    # Create keywords and news
    keyword_reliance, _ = Keyword.objects.get_or_create(name='RELIANCE')
    keyword_tcs, _ = Keyword.objects.get_or_create(name='TCS')

    # Add keywords to user searches
    profile.searches.add(keyword_reliance, keyword_tcs)

    # Create sample news articles
    et_source = Source.objects.get(id_name='ET')
    toi_source = Source.objects.get(id_name='TOI')

    news_data = [
        {
            'title': 'Reliance Industries Reports Strong Q3 Earnings, Beats Estimates',
            'summary': 'Reliance Industries reported a 25% jump in quarterly profits, driven by strong performance in retail and telecom segments.',
            'link': 'https://economictimes.indiatimes.com/reliance-q3-2025',
            'keyword': keyword_reliance,
            'source': et_source,
            'impact_rating': 0.75,
            'sentiment_confidence': 0.85,
            'sentiment_explanation': 'Strong quarterly results indicate robust business growth across multiple segments, likely to boost investor confidence.',
            'mentioned_tickers': ['RELIANCE'],
        },
        {
            'title': 'TCS Wins $500 Million Deal with Fortune 500 Company',
            'summary': 'Tata Consultancy Services secured a major five-year contract for digital transformation services.',
            'link': 'https://economictimes.indiatimes.com/tcs-deal-2025',
            'keyword': keyword_tcs,
            'source': et_source,
            'impact_rating': 0.65,
            'sentiment_confidence': 0.80,
            'sentiment_explanation': 'Major contract win demonstrates strong demand for TCS services and strengthens order book.',
            'mentioned_tickers': ['TCS'],
        },
        {
            'title': 'Market Volatility: Sensex Drops 500 Points on Global Concerns',
            'summary': 'Indian stock markets faced selling pressure amid global economic uncertainties.',
            'link': 'https://timesofindia.indiatimes.com/market-drop-2025',
            'keyword': keyword_reliance,
            'source': toi_source,
            'impact_rating': -0.45,
            'sentiment_confidence': 0.70,
            'sentiment_explanation': 'Broad market decline reflects investor caution due to global economic headwinds.',
            'mentioned_tickers': [],
        },
        {
            'title': 'TCS Announces Expansion Plans in North America',
            'summary': 'TCS plans to hire 10,000 employees in the US and Canada over the next two years.',
            'link': 'https://economictimes.indiatimes.com/tcs-expansion-2025',
            'keyword': keyword_tcs,
            'source': et_source,
            'impact_rating': 0.50,
            'sentiment_confidence': 0.75,
            'sentiment_explanation': 'Expansion plans indicate strong business outlook and commitment to strategic markets.',
            'mentioned_tickers': ['TCS'],
        },
    ]

    for data in news_data:
        News.objects.get_or_create(
            link=data['link'],
            defaults={
                'title': data['title'],
                'content_summary': data['summary'],
                'keyword': data['keyword'],
                'source': data['source'],
                'impact_rating': data['impact_rating'],
                'sentiment_confidence': data.get('sentiment_confidence', 0),
                'sentiment_explanation': data.get('sentiment_explanation', ''),
                'mentioned_tickers': data.get('mentioned_tickers', []),
                'date': timezone.now(),
            }
        )

    print(f"✓ Created {len(news_data)} news articles")
    print("\nTest data setup complete!")


async def capture_screenshots():
    """Capture screenshots using Playwright."""
    print("\nLaunching browser...")

    # Ensure screenshots directory exists
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='en-US'
        )
        page = await context.new_page()

        try:
            # 1. Login Page
            print("Capturing login page...")
            await page.goto(f'{BASE_URL}/accounts/login/')
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=str(SCREENSHOTS_DIR / '01-login.png'), full_page=True)
            print("✓ Saved: 01-login.png")

            # Perform login
            await page.fill('input[name="username"]', USERNAME)
            await page.fill('input[name="password"]', PASSWORD)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')

            # 2. Search Page (Main Interface)
            print("Capturing search page...")
            await page.goto(f'{BASE_URL}/search/')
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=str(SCREENSHOTS_DIR / '02-search-page.png'), full_page=True)
            print("✓ Saved: 02-search-page.png")

            # 3. Perform Search and Capture Results
            print("Capturing search results...")
            await page.fill('input[name="keyword"]', 'RELIANCE')
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)  # Wait for any dynamic content
            await page.screenshot(path=str(SCREENSHOTS_DIR / '03-search-results.png'), full_page=True)
            print("✓ Saved: 03-search-results.png")

            # 4. News Detail Page
            print("Capturing news detail page...")
            # Click on first news article
            news = await News.objects.filter(keyword__name='RELIANCE').first()
            if news:
                await page.goto(f'{BASE_URL}/news/{news.id}/')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=str(SCREENSHOTS_DIR / '04-news-detail.png'), full_page=True)
                print("✓ Saved: 04-news-detail.png")

            # 5. Past Searches
            print("Capturing past searches page...")
            await page.goto(f'{BASE_URL}/past-searches/')
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=str(SCREENSHOTS_DIR / '05-past-searches.png'), full_page=True)
            print("✓ Saved: 05-past-searches.png")

            # 6. Watchlist Management
            print("Capturing watchlist page...")
            await page.goto(f'{BASE_URL}/add-stocks/')
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path=str(SCREENSHOTS_DIR / '06-watchlist.png'), full_page=True)
            print("✓ Saved: 06-watchlist.png")

            # 7. Admin Panel (if accessible)
            try:
                print("Capturing admin panel...")
                await page.goto(f'{BASE_URL}/admin/')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=str(SCREENSHOTS_DIR / '07-admin.png'), full_page=True)
                print("✓ Saved: 07-admin.png")
            except Exception as e:
                print(f"⚠ Could not capture admin panel: {e}")

            print("\n✓ All screenshots captured successfully!")

        except Exception as e:
            print(f"✗ Error capturing screenshots: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await browser.close()


async def main():
    """Main execution function."""
    print("=" * 60)
    print("News Analyser - Screenshot Generator")
    print("=" * 60)

    # Setup test data
    await setup_test_data()

    # Capture screenshots
    await capture_screenshots()

    print("\n" + "=" * 60)
    print("Screenshot generation complete!")
    print(f"Screenshots saved to: {SCREENSHOTS_DIR}")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
