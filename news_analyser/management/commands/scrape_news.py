"""
Django Management Command for Manual News Scraping
Usage:
    python manage.py scrape_news                    # Scrape all feeds
    python manage.py scrape_news --feed et_markets  # Scrape specific feed
    python manage.py scrape_news --test             # Test scraping system
    python manage.py scrape_news --list             # List available feeds
"""

from django.core.management.base import BaseCommand, CommandError
from news_analyser.scraper_refactored import NewsScraperRefactored
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape news from configured RSS feeds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--feed',
            type=str,
            help='Scrape a specific feed by key (e.g., economic_times_markets)'
        )

        parser.add_argument(
            '--test',
            action='store_true',
            help='Test the scraping system with one feed'
        )

        parser.add_argument(
            '--list',
            action='store_true',
            help='List all available feeds'
        )

        parser.add_argument(
            '--no-save',
            action='store_true',
            help='Scrape but don\'t save to database (for testing)'
        )

        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Trigger sentiment analysis for newly scraped articles'
        )

    def handle(self, *args, **options):
        scraper = NewsScraperRefactored(timeout=30, max_retries=3)

        # List available feeds
        if options['list']:
            self._list_feeds(scraper)
            return

        # Test mode
        if options['test']:
            self._test_scraping(scraper, options)
            return

        # Scrape specific feed
        if options['feed']:
            self._scrape_single_feed(scraper, options['feed'], options)
            return

        # Scrape all feeds
        self._scrape_all_feeds(scraper, options)

    def _list_feeds(self, scraper):
        """List all available RSS feeds"""
        self.stdout.write(self.style.SUCCESS('\nAvailable RSS Feeds:'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        for feed_key, feed_config in scraper.RSS_FEEDS.items():
            self.stdout.write(
                f"  {self.style.WARNING(feed_key)}\n"
                f"    Name: {feed_config['name']}\n"
                f"    Category: {feed_config['category']}\n"
                f"    URL: {feed_config['url']}\n"
            )

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS(f'Total: {len(scraper.RSS_FEEDS)} feeds\n'))

    def _test_scraping(self, scraper, options):
        """Test scraping system with one feed"""
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('TESTING SCRAPING SYSTEM'))
        self.stdout.write(self.style.SUCCESS('=' * 80 + '\n'))

        # Test with the first feed
        test_feed_key = list(scraper.RSS_FEEDS.keys())[0]
        self.stdout.write(f"Testing with feed: {self.style.WARNING(test_feed_key)}\n")

        result = scraper.scrape_feed(test_feed_key)

        if result['success']:
            self.stdout.write(self.style.SUCCESS(f"✓ Successfully scraped {len(result['articles'])} articles\n"))

            if result['articles']:
                # Show sample article
                sample = result['articles'][0]
                self.stdout.write("Sample article:")
                self.stdout.write(f"  Title: {sample['title']}")
                self.stdout.write(f"  Link: {sample['link']}")
                self.stdout.write(f"  Published: {sample['published_at']}")
                self.stdout.write(f"  Summary: {sample['content_summary'][:100]}...\n")

                # Test database save
                if not options['no_save']:
                    save_stats = scraper.save_articles_to_db(
                        articles=result['articles'][:5],  # Save first 5 as test
                        source_name=result['feed_name']
                    )
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ Database save test: {save_stats['saved']} saved, "
                        f"{save_stats['duplicates']} duplicates, {save_stats['errors']} errors"
                    ))

            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.SUCCESS('TEST RESULT: PASSED ✓'))
            self.stdout.write('=' * 80 + '\n')

        else:
            self.stdout.write(self.style.ERROR(f"✗ Test failed: {result.get('error')}\n"))
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.ERROR('TEST RESULT: FAILED ✗'))
            self.stdout.write('=' * 80 + '\n')

    def _scrape_single_feed(self, scraper, feed_key, options):
        """Scrape a single feed"""
        self.stdout.write(self.style.SUCCESS(f'\nScraping feed: {feed_key}'))
        self.stdout.write(self.style.SUCCESS('=' * 80 + '\n'))

        result = scraper.scrape_feed(feed_key)

        if result['success']:
            self.stdout.write(self.style.SUCCESS(
                f"✓ Successfully scraped {len(result['articles'])} articles from {result['feed_name']}"
            ))

            if result['articles'] and not options['no_save']:
                # Save to database
                save_stats = scraper.save_articles_to_db(
                    articles=result['articles'],
                    source_name=result['feed_name']
                )

                self.stdout.write(self.style.SUCCESS(
                    f"✓ Database save: {save_stats['saved']} new articles, "
                    f"{save_stats['duplicates']} duplicates, {save_stats['errors']} errors"
                ))

                # Trigger analysis if requested
                if options['analyze'] and save_stats['saved'] > 0:
                    from news_analyser.tasks_scraping import analyze_recent_articles
                    analyze_recent_articles.delay(hours=1)
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ Triggered sentiment analysis for recent articles"
                    ))

            elif options['no_save']:
                self.stdout.write(self.style.WARNING('  --no-save flag set, skipping database save'))

        else:
            self.stdout.write(self.style.ERROR(f"✗ Scraping failed: {result.get('error')}"))

        self.stdout.write('')

    def _scrape_all_feeds(self, scraper, options):
        """Scrape all configured feeds"""
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('SCRAPING ALL NEWS FEEDS'))
        self.stdout.write(self.style.SUCCESS('=' * 80 + '\n'))

        results = scraper.scrape_all_feeds()

        # Print summary
        self.stdout.write(f"\nScraping Summary:")
        self.stdout.write(f"  Total Feeds: {results['total_feeds']}")
        self.stdout.write(self.style.SUCCESS(f"  Successful: {results['successful_feeds']}"))
        if results['failed_feeds'] > 0:
            self.stdout.write(self.style.ERROR(f"  Failed: {results['failed_feeds']}"))
        self.stdout.write(f"  Total Articles Found: {results['total_articles']}\n")

        # Save to database if not in no-save mode
        if not options['no_save']:
            total_saved = 0
            total_duplicates = 0
            total_errors = 0

            for feed_result in results['feeds']:
                if feed_result['success'] and feed_result['articles']:
                    save_stats = scraper.save_articles_to_db(
                        articles=feed_result['articles'],
                        source_name=feed_result['feed_name']
                    )

                    total_saved += save_stats['saved']
                    total_duplicates += save_stats['duplicates']
                    total_errors += save_stats['errors']

                    if save_stats['saved'] > 0:
                        self.stdout.write(
                            f"  ✓ {feed_result['feed_name']}: "
                            f"{save_stats['saved']} new, {save_stats['duplicates']} duplicates"
                        )

            self.stdout.write(f"\nDatabase Save Summary:")
            self.stdout.write(self.style.SUCCESS(f"  New Articles Saved: {total_saved}"))
            self.stdout.write(f"  Duplicates Skipped: {total_duplicates}")
            if total_errors > 0:
                self.stdout.write(self.style.ERROR(f"  Errors: {total_errors}"))

            # Trigger analysis if requested
            if options['analyze'] and total_saved > 0:
                from news_analyser.tasks_scraping import analyze_recent_articles
                analyze_recent_articles.delay(hours=1)
                self.stdout.write(self.style.SUCCESS(
                    f"\n✓ Triggered sentiment analysis for {total_saved} new articles"
                ))

        else:
            self.stdout.write(self.style.WARNING('\n--no-save flag set, skipping database save'))

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('SCRAPING COMPLETE'))
        self.stdout.write('=' * 80 + '\n')
