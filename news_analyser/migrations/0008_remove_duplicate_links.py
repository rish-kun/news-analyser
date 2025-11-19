# Generated manually to fix UNIQUE constraint violation
from django.db import migrations


def remove_duplicate_links(apps, schema_editor):
    """
    Remove duplicate news entries, keeping only the oldest one for each link.
    """
    News = apps.get_model('news_analyser', 'News')
    
    # Get all links that have duplicates
    from django.db.models import Count
    duplicate_links = (
        News.objects.values('link')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
        .values_list('link', flat=True)
    )
    
    for link in duplicate_links:
        # Get all news items with this link, ordered by date (oldest first)
        news_items = News.objects.filter(link=link).order_by('date')
        
        # Keep the first (oldest) one, delete the rest
        items_to_delete = news_items[1:]
        for item in items_to_delete:
            item.delete()


def reverse_migration(apps, schema_editor):
    # This migration is not reversible as we're deleting data
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('news_analyser', '0007_alter_userprofile_searches'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_links, reverse_migration),
    ]
