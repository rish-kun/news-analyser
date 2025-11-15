from django.contrib import admin
from news_analyser.models import News, Keyword, Source, SentimentScore, Stock, Sector, UserProfile


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'source', 'published_at', 'is_analyzed', 'impact_rating']
    list_filter = ['source', 'is_analyzed', 'published_at', 'scraped_at']
    search_fields = ['title', 'content_summary', 'content']
    date_hierarchy = 'published_at'
    readonly_fields = ['scraped_at', 'updated_at', 'content_hash']
    filter_horizontal = ['tickers', 'sectors']


@admin.register(SentimentScore)
class SentimentScoreAdmin(admin.ModelAdmin):
    list_display = ['news', 'ticker', 'sector', 'sentiment_score', 'sentiment_label', 'confidence', 'created_at']
    list_filter = ['sentiment_label', 'model_used', 'created_at']
    search_fields = ['news__title']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbol', 'sector']
    list_filter = ['sector']
    search_fields = ['name', 'symbol']
    filter_horizontal = ['keywords']


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ['name', 'search_fields']
    search_fields = ['name']


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'id_name', 'is_active', 'scrape_frequency', 'last_scraped']
    list_filter = ['is_active']
    search_fields = ['name', 'id_name']


admin.site.register(Keyword)
admin.site.register(UserProfile)
