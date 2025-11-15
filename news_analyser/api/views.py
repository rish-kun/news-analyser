"""
API ViewSets for News Analyser
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.db.models import Q, Avg, Count
from datetime import timedelta
from django.utils import timezone

from news_analyser.models import News, SentimentScore, Stock, Sector, Source, UserProfile
from .serializers import (
    NewsListSerializer, NewsDetailSerializer,
    SentimentScoreSerializer, StockSerializer, SectorSerializer,
    SourceSerializer, TickerSentimentSerializer, SectorSentimentSerializer,
    MarketSummarySerializer, UserProfileSerializer
)
from news_analyser.tasks import analyze_article_sentiment, aggregate_ticker_sentiment
from news_analyser.sentiment.sector_analyzer import SectorSentimentAnalyzer


class NewsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for news articles

    list: Get paginated list of news articles
    retrieve: Get detailed information about a specific article
    search: Search news by ticker or keyword
    recent: Get recent news articles
    """
    queryset = News.objects.all().select_related('source').prefetch_related('tickers', 'sectors', 'sentiment_scores')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source', 'is_analyzed', 'published_at']
    search_fields = ['title', 'content_summary', 'content']
    ordering_fields = ['published_at', 'scraped_at', 'impact_rating']
    ordering = ['-published_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return NewsDetailSerializer
        return NewsListSerializer

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent news articles"""
        hours = int(request.query_params.get('hours', 24))
        cutoff_time = timezone.now() - timedelta(hours=hours)

        recent_news = self.get_queryset().filter(
            published_at__gte=cutoff_time
        )[:50]

        serializer = self.get_serializer(recent_news, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search news by ticker symbol or keyword"""
        ticker = request.query_params.get('ticker')
        keyword = request.query_params.get('q')

        queryset = self.get_queryset()

        if ticker:
            queryset = queryset.filter(tickers__symbol__iexact=ticker)

        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) |
                Q(content_summary__icontains=keyword) |
                Q(content__icontains=keyword)
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """Trigger sentiment analysis for a specific article"""
        news = self.get_object()

        if news.is_analyzed:
            return Response({
                'message': 'Article already analyzed',
                'sentiment_score': news.impact_rating
            })

        # Trigger analysis task
        task = analyze_article_sentiment.delay(news.id)

        return Response({
            'message': 'Analysis queued',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'])
    def by_sentiment(self, request):
        """Get news filtered by sentiment range"""
        min_sentiment = float(request.query_params.get('min', -1.0))
        max_sentiment = float(request.query_params.get('max', 1.0))

        news_ids = SentimentScore.objects.filter(
            sentiment_score__gte=min_sentiment,
            sentiment_score__lte=max_sentiment
        ).values_list('news_id', flat=True).distinct()

        queryset = self.get_queryset().filter(id__in=news_ids)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SentimentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for sentiment analysis

    ticker_sentiment: Get sentiment for a specific ticker
    sector_sentiment: Get sentiment for a sector
    market_summary: Get overall market sentiment summary
    """
    queryset = SentimentScore.objects.all()
    serializer_class = SentimentScoreSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['ticker', 'sector', 'sentiment_label']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'], url_path='ticker/(?P<symbol>[^/.]+)')
    def ticker_sentiment(self, request, symbol=None):
        """Get aggregated sentiment for a ticker"""
        hours = int(request.query_params.get('hours', 24))

        # Check cache
        cache_key = f'ticker_sentiment_{symbol}_{hours}h'
        cached_data = cache.get(cache_key)

        if cached_data:
            serializer = TickerSentimentSerializer(cached_data)
            return Response(serializer.data)

        # Trigger aggregation task
        task = aggregate_ticker_sentiment.delay(symbol, hours)

        # Wait briefly for task to complete
        try:
            result = task.get(timeout=5)
            if result.get('status') == 'success':
                del result['status']
                serializer = TickerSentimentSerializer(result)
                return Response(serializer.data)
        except:
            pass

        return Response({
            'message': 'Sentiment calculation in progress',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='sector/(?P<sector_name>[^/.]+)')
    def sector_sentiment(self, request, sector_name=None):
        """Get sentiment for a specific sector"""
        hours = int(request.query_params.get('hours', 24))

        analyzer = SectorSentimentAnalyzer()
        sentiment_data = analyzer.get_sector_sentiment(sector_name, hours)

        if sentiment_data:
            serializer = SectorSentimentSerializer(sentiment_data)
            return Response(serializer.data)

        return Response({
            'error': 'No sentiment data available for this sector'
        }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def market_summary(self, request):
        """Get overall market sentiment summary"""
        # Check cache
        cached_summary = cache.get('daily_market_summary')

        if cached_summary:
            serializer = MarketSummarySerializer(cached_summary)
            return Response(serializer.data)

        # Generate new summary
        from news_analyser.tasks import generate_market_summary
        task = generate_market_summary.delay()

        try:
            result = task.get(timeout=10)
            if result.get('status') == 'success':
                serializer = MarketSummarySerializer(result['summary'])
                return Response(serializer.data)
        except:
            pass

        return Response({
            'message': 'Market summary generation in progress'
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending sentiment changes"""
        hours = int(request.query_params.get('hours', 24))

        analyzer = SectorSentimentAnalyzer()
        trending_sectors = analyzer.get_trending_sectors(hours, limit=10)

        return Response(trending_sectors)

    @action(detail=False, methods=['get'])
    def rotation_signals(self, request):
        """Get sector rotation signals"""
        hours = int(request.query_params.get('hours', 24))

        analyzer = SectorSentimentAnalyzer()
        signals = analyzer.get_sector_rotation_signals(hours)

        return Response(signals)


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for stocks

    list: Get all stocks
    retrieve: Get specific stock details
    sentiment_history: Get sentiment history for a stock
    """
    queryset = Stock.objects.all().select_related('sector')
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sector']
    search_fields = ['name', 'symbol']
    ordering_fields = ['name', 'symbol']
    ordering = ['symbol']

    @action(detail=True, methods=['get'])
    def sentiment_history(self, request, pk=None):
        """Get sentiment history for a stock"""
        stock = self.get_object()
        hours = int(request.query_params.get('hours', 168))  # Default 1 week

        cutoff_time = timezone.now() - timedelta(hours=hours)

        sentiments = SentimentScore.objects.filter(
            ticker=stock,
            created_at__gte=cutoff_time
        ).order_by('-created_at')

        serializer = SentimentScoreSerializer(sentiments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def recent_news(self, request, pk=None):
        """Get recent news mentioning this stock"""
        stock = self.get_object()
        hours = int(request.query_params.get('hours', 24))

        cutoff_time = timezone.now() - timedelta(hours=hours)

        news = News.objects.filter(
            tickers=stock,
            published_at__gte=cutoff_time
        ).order_by('-published_at')[:20]

        serializer = NewsListSerializer(news, many=True)
        return Response(serializer.data)


class SectorViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for sectors"""
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['get'])
    def stocks(self, request, pk=None):
        """Get all stocks in a sector"""
        sector = self.get_object()
        stocks = Stock.objects.filter(sector=sector)
        serializer = StockSerializer(stocks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def sentiment(self, request, pk=None):
        """Get sector sentiment"""
        sector = self.get_object()
        hours = int(request.query_params.get('hours', 24))

        analyzer = SectorSentimentAnalyzer()
        sentiment_data = analyzer.get_sector_sentiment(sector.name, hours)

        if sentiment_data:
            serializer = SectorSentimentSerializer(sentiment_data)
            return Response(serializer.data)

        return Response({
            'error': 'No sentiment data available'
        }, status=status.HTTP_404_NOT_FOUND)


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for user profiles"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own profile
        return UserProfile.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        """Add stock to user's watchlist"""
        profile = self.get_object()
        stock_id = request.data.get('stock_id')

        try:
            stock = Stock.objects.get(id=stock_id)
            profile.stocks.add(stock)
            return Response({'message': 'Stock added to watchlist'})
        except Stock.DoesNotExist:
            return Response({'error': 'Stock not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def remove_stock(self, request, pk=None):
        """Remove stock from user's watchlist"""
        profile = self.get_object()
        stock_id = request.data.get('stock_id')

        try:
            stock = Stock.objects.get(id=stock_id)
            profile.stocks.remove(stock)
            return Response({'message': 'Stock removed from watchlist'})
        except Stock.DoesNotExist:
            return Response({'error': 'Stock not found'}, status=status.HTTP_404_NOT_FOUND)
