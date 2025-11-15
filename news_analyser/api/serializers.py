"""
DRF Serializers for News Analyser API
"""

from rest_framework import serializers
from news_analyser.models import News, SentimentScore, Stock, Sector, Source, UserProfile, Keyword


class StockSerializer(serializers.ModelSerializer):
    """Serializer for Stock model"""

    class Meta:
        model = Stock
        fields = ['id', 'name', 'symbol', 'sector']


class SectorSerializer(serializers.ModelSerializer):
    """Serializer for Sector model"""

    class Meta:
        model = Sector
        fields = ['id', 'name', 'search_fields']


class SourceSerializer(serializers.ModelSerializer):
    """Serializer for Source model"""

    class Meta:
        model = Source
        fields = ['id', 'id_name', 'name', 'url', 'is_active', 'last_scraped']


class SentimentScoreSerializer(serializers.ModelSerializer):
    """Serializer for SentimentScore model"""
    ticker_symbol = serializers.CharField(source='ticker.symbol', read_only=True, allow_null=True)
    ticker_name = serializers.CharField(source='ticker.name', read_only=True, allow_null=True)
    sector_name = serializers.CharField(source='sector.name', read_only=True, allow_null=True)

    class Meta:
        model = SentimentScore
        fields = [
            'id', 'ticker', 'ticker_symbol', 'ticker_name',
            'sector', 'sector_name',
            'gemini_score', 'finbert_score', 'vader_score', 'textblob_score',
            'sentiment_score', 'sentiment_label', 'confidence',
            'entities', 'keywords_extracted', 'analysis_details',
            'created_at', 'model_used'
        ]


class NewsListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for news list views"""
    source_name = serializers.CharField(source='source.name', read_only=True)
    tickers_count = serializers.SerializerMethodField()
    average_sentiment = serializers.SerializerMethodField()

    class Meta:
        model = News
        fields = [
            'id', 'title', 'content_summary', 'link',
            'published_at', 'scraped_at', 'source_name',
            'impact_rating', 'is_analyzed', 'image_url',
            'tickers_count', 'average_sentiment'
        ]

    def get_tickers_count(self, obj):
        return obj.tickers.count()

    def get_average_sentiment(self, obj):
        scores = obj.sentiment_scores.all()
        if scores.exists():
            from django.db.models import Avg
            avg = scores.aggregate(Avg('sentiment_score'))['sentiment_score__avg']
            return round(avg, 3) if avg else None
        return None


class NewsDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual news articles"""
    source = SourceSerializer(read_only=True)
    tickers = StockSerializer(many=True, read_only=True)
    sectors = SectorSerializer(many=True, read_only=True)
    sentiment_scores = SentimentScoreSerializer(many=True, read_only=True)

    class Meta:
        model = News
        fields = [
            'id', 'title', 'content_summary', 'content', 'link',
            'author', 'image_url', 'tags',
            'published_at', 'scraped_at', 'updated_at',
            'source', 'impact_rating', 'is_analyzed',
            'tickers', 'sectors', 'sentiment_scores'
        ]


class TickerSentimentSerializer(serializers.Serializer):
    """Serializer for ticker sentiment aggregation"""
    ticker = serializers.CharField()
    average_sentiment = serializers.FloatField()
    weighted_sentiment = serializers.FloatField()
    article_count = serializers.IntegerField()
    time_window_hours = serializers.IntegerField()
    timestamp = serializers.DateTimeField()


class SectorSentimentSerializer(serializers.Serializer):
    """Serializer for sector sentiment data"""
    sector = serializers.CharField()
    average_sentiment = serializers.FloatField()
    article_count = serializers.IntegerField()
    distribution = serializers.DictField()
    time_period_hours = serializers.IntegerField()
    timestamp = serializers.DateTimeField()


class MarketSummarySerializer(serializers.Serializer):
    """Serializer for market summary"""
    date = serializers.DateField()
    market_sentiment = serializers.FloatField()
    total_articles = serializers.IntegerField()
    sector_sentiments = serializers.DictField()
    trending_sectors = serializers.ListField()
    rotation_signals = serializers.ListField()
    generated_at = serializers.DateTimeField()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    username = serializers.CharField(source='user.username', read_only=True)
    stocks = StockSerializer(many=True, read_only=True)
    searches = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'preferences', 'stocks', 'searches']
