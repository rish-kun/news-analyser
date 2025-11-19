"""
Enhanced views with comprehensive sentiment analysis features
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count, Q, Max
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import asyncio

from .models import News, Keyword, Stock, Sector, SentimentScore, UserProfile, Source
from .tasks import analyze_article_sentiment, scrape_all_sources, aggregate_ticker_sentiment
from .sentiment.sector_analyzer import SectorSentimentAnalyzer
from .sentiment.analyzer import AdvancedSentimentAnalyzer
from .rss import check_keywords
from .forms import UserRegistrationForm, UserSettingsForm
from django.contrib.auth import login


# ============================================================================
# DASHBOARD & HOME VIEWS
# ============================================================================

class DashboardView(LoginRequiredMixin, View):
    """
    Main dashboard showing market overview and sentiment summary
    """

    def get(self, request):
        # Get user's watchlist
        user_stocks = request.user.profile.stocks.all()[:10]

        # Get recent news (last 24 hours)
        cutoff_time = timezone.now() - timedelta(hours=24)
        recent_news = News.objects.filter(
            published_at__gte=cutoff_time,
            is_analyzed=True
        ).select_related('source').prefetch_related('tickers', 'sectors')[:20]

        # Get market sentiment summary
        market_stats = SentimentScore.objects.filter(
            created_at__gte=cutoff_time
        ).aggregate(
            avg_sentiment=Avg('sentiment_score'),
            count=Count('id')
        )

        # Get sentiment distribution
        distribution = {
            'very_positive': SentimentScore.objects.filter(
                created_at__gte=cutoff_time,
                sentiment_label='very_positive'
            ).count(),
            'positive': SentimentScore.objects.filter(
                created_at__gte=cutoff_time,
                sentiment_label='positive'
            ).count(),
            'neutral': SentimentScore.objects.filter(
                created_at__gte=cutoff_time,
                sentiment_label='neutral'
            ).count(),
            'negative': SentimentScore.objects.filter(
                created_at__gte=cutoff_time,
                sentiment_label='negative'
            ).count(),
            'very_negative': SentimentScore.objects.filter(
                created_at__gte=cutoff_time,
                sentiment_label='very_negative'
            ).count(),
        }

        # Get trending sectors
        sector_analyzer = SectorSentimentAnalyzer()
        trending_sectors = sector_analyzer.get_trending_sectors(hours=24, limit=5)

        # Get sentiment for user's watchlist stocks
        watchlist_sentiment = []
        for stock in user_stocks:
            recent_sentiment = SentimentScore.objects.filter(
                ticker=stock,
                created_at__gte=cutoff_time
            ).aggregate(
                avg=Avg('sentiment_score'),
                count=Count('id')
            )

            if recent_sentiment['count']:
                watchlist_sentiment.append({
                    'stock': stock,
                    'sentiment': recent_sentiment['avg'],
                    'article_count': recent_sentiment['count']
                })

        context = {
            'user_stocks': user_stocks,
            'recent_news': recent_news,
            'market_stats': market_stats,
            'distribution': distribution,
            'trending_sectors': trending_sectors,
            'watchlist_sentiment': watchlist_sentiment,
        }

        return render(request, 'news_analyser/dashboard.html', context)


# ============================================================================
# SEARCH VIEWS (Enhanced)
# ============================================================================

class SearchView(LoginRequiredMixin, View):
    """
    Enhanced search view with better UI
    """

    def get(self, request):
        user_stocks = request.user.profile.stocks.all()
        recent_keywords = request.user.profile.searches.all()[:5]

        # Get some quick stats
        total_news = News.objects.filter(is_analyzed=True).count()
        total_stocks = Stock.objects.count()

        context = {
            'user_stocks': user_stocks,
            'recent_keywords': recent_keywords,
            'total_news': total_news,
            'total_stocks': total_stocks,
        }

        return render(request, 'news_analyser/search.html', context)

    def post(self, request):
        search_type = request.POST.get('search_type')

        if search_type == 'keyword':
            kwds = [k.strip() for k in request.POST.get('keyword', '').split(',') if k.strip()]
        else:
            kwds = request.POST.getlist('stocks')

        if not kwds:
            messages.error(request, 'Please provide search keywords or select stocks.')
            return redirect('news_analyser:search')

        news = check_keywords(kwds)
        kwd_link = {}
        k_obj = None

        for k, n in news.items():
            k_obj, created = Keyword.objects.get_or_create(name=k)
            request.user.profile.searches.add(k_obj)

            for i in n:
                n_obj = News.parse_news(i, k_obj)
                kwd_link[k] = [n_obj] + kwd_link.get(k, [])

        # Trigger sentiment analysis for new articles
        for k, n in kwd_link.items():
            for i in n:
                if not i.is_analyzed:
                    analyze_article_sentiment.delay(i.id)

        if k_obj:
            return redirect(reverse('news_analyser:search_results', args=[k_obj.id]))
        else:
            messages.info(request, 'No news found for the given keywords.')
            return redirect('news_analyser:search')


@login_required
def search_result(request, news_id=None):
    """
    Enhanced search results with sentiment scores
    """
    kwd = get_object_or_404(Keyword, id=news_id)
    news_list = kwd.news.all().select_related('source').prefetch_related(
        'tickers', 'sectors', 'sentiment_scores'
    ).order_by('-published_at')

    # Calculate aggregate stats
    analyzed_count = news_list.filter(is_analyzed=True).count()
    avg_sentiment = news_list.filter(is_analyzed=True).aggregate(
        Avg('impact_rating')
    )['impact_rating__avg'] or 0

    context = {
        'kw_link': {kwd: news_list},
        'keyword': kwd,
        'total_count': news_list.count(),
        'analyzed_count': analyzed_count,
        'avg_sentiment': avg_sentiment,
    }

    return render(request, 'news_analyser/result.html', context)


# ============================================================================
# STOCK/TICKER VIEWS
# ============================================================================

class TickerDetailView(LoginRequiredMixin, View):
    """
    Detailed view for a specific stock ticker with sentiment history
    """

    def get(self, request, symbol):
        stock = get_object_or_404(Stock, symbol=symbol.upper())

        # Get time range from query params
        hours = int(request.GET.get('hours', 168))  # Default 1 week
        cutoff_time = timezone.now() - timedelta(hours=hours)

        # Get recent news for this ticker
        recent_news = News.objects.filter(
            tickers=stock,
            published_at__gte=cutoff_time
        ).select_related('source').prefetch_related(
            'sentiment_scores'
        ).order_by('-published_at')[:50]

        # Get sentiment history
        sentiment_history = SentimentScore.objects.filter(
            ticker=stock,
            created_at__gte=cutoff_time
        ).order_by('-created_at')[:100]

        # Calculate stats
        stats = sentiment_history.aggregate(
            avg_sentiment=Avg('sentiment_score'),
            avg_confidence=Avg('confidence'),
            count=Count('id')
        )

        # Get sentiment distribution
        distribution = {
            label: sentiment_history.filter(sentiment_label=label).count()
            for label, _ in SentimentScore._meta.get_field('sentiment_label').choices
        }

        # Prepare data for charts
        chart_data = [
            {
                'date': score.created_at.isoformat(),
                'sentiment': score.sentiment_score,
                'confidence': score.confidence,
            }
            for score in sentiment_history
        ]

        context = {
            'stock': stock,
            'recent_news': recent_news,
            'sentiment_history': sentiment_history,
            'stats': stats,
            'distribution': distribution,
            'chart_data': chart_data,
            'hours': hours,
        }

        return render(request, 'news_analyser/ticker_detail.html', context)


@login_required
def watchlist_view(request):
    """
    User's stock watchlist with sentiment overview
    """
    user_stocks = request.user.profile.stocks.all()

    cutoff_time = timezone.now() - timedelta(hours=24)

    watchlist_data = []
    for stock in user_stocks:
        # Get latest sentiment
        latest_sentiment = SentimentScore.objects.filter(
            ticker=stock,
            created_at__gte=cutoff_time
        ).aggregate(
            avg=Avg('sentiment_score'),
            count=Count('id')
        )

        # Get recent news count
        news_count = News.objects.filter(
            tickers=stock,
            published_at__gte=cutoff_time
        ).count()

        watchlist_data.append({
            'stock': stock,
            'sentiment': latest_sentiment['avg'],
            'sentiment_count': latest_sentiment['count'],
            'news_count': news_count,
        })

    # Sort by sentiment (most positive first)
    watchlist_data.sort(key=lambda x: x['sentiment'] or 0, reverse=True)

    context = {
        'watchlist_data': watchlist_data,
    }

    return render(request, 'news_analyser/watchlist.html', context)


# ============================================================================
# SECTOR VIEWS
# ============================================================================

class SectorAnalysisView(LoginRequiredMixin, View):
    """
    Sector analysis dashboard
    """

    def get(self, request):
        sector_analyzer = SectorSentimentAnalyzer()

        # Get time range
        hours = int(request.GET.get('hours', 24))

        # Get all sector sentiments
        all_sectors = sector_analyzer.get_all_sectors_sentiment(hours=hours)

        # Get trending sectors
        trending = sector_analyzer.get_trending_sectors(hours=hours, limit=10)

        # Get rotation signals
        rotation_signals = sector_analyzer.get_sector_rotation_signals(hours=hours)

        context = {
            'all_sectors': all_sectors,
            'trending': trending,
            'rotation_signals': rotation_signals,
            'hours': hours,
        }

        return render(request, 'news_analyser/sector_analysis.html', context)


class SectorDetailView(LoginRequiredMixin, View):
    """
    Detailed view for a specific sector
    """

    def get(self, request, sector_name):
        sector = get_object_or_404(Sector, name__iexact=sector_name)

        # Get time range
        hours = int(request.GET.get('hours', 168))
        cutoff_time = timezone.now() - timedelta(hours=hours)

        # Get stocks in sector
        stocks_in_sector = Stock.objects.filter(sector=sector)

        # Get recent news for this sector
        recent_news = News.objects.filter(
            sectors=sector,
            published_at__gte=cutoff_time
        ).select_related('source').order_by('-published_at')[:50]

        # Get sentiment history
        sentiment_history = SentimentScore.objects.filter(
            sector=sector,
            created_at__gte=cutoff_time
        ).order_by('-created_at')

        # Calculate stats
        stats = sentiment_history.aggregate(
            avg_sentiment=Avg('sentiment_score'),
            count=Count('id')
        )

        # Get sentiment analyzer
        sector_analyzer = SectorSentimentAnalyzer()
        sector_sentiment = sector_analyzer.get_sector_sentiment(sector.name, hours)

        context = {
            'sector': sector,
            'stocks_in_sector': stocks_in_sector,
            'recent_news': recent_news,
            'sentiment_history': sentiment_history,
            'stats': stats,
            'sector_sentiment': sector_sentiment,
            'hours': hours,
        }

        return render(request, 'news_analyser/sector_detail.html', context)


# ============================================================================
# NEWS DETAIL VIEWS (Enhanced)
# ============================================================================

class NewsAnalysisView(LoginRequiredMixin, View):
    """
    Enhanced news analysis view with full sentiment breakdown
    """

    def get(self, request, news_id):
        news = get_object_or_404(News, id=news_id)

        # Get all sentiment scores for this news
        sentiment_scores = news.sentiment_scores.all().select_related('ticker', 'sector')

        # Get primary sentiment (general/overall)
        primary_sentiment = sentiment_scores.filter(ticker__isnull=True, sector__isnull=True).first()

        # Get ticker-specific sentiments
        ticker_sentiments = sentiment_scores.filter(ticker__isnull=False)

        # Get sector-specific sentiments
        sector_sentiments = sentiment_scores.filter(sector__isnull=False)

        context = {
            'news': news,
            'sentiment_scores': sentiment_scores,
            'primary_sentiment': primary_sentiment,
            'ticker_sentiments': ticker_sentiments,
            'sector_sentiments': sector_sentiments,
        }

        return render(request, 'news_analyser/news_analysis.html', context)

    def post(self, request, news_id):
        news = get_object_or_404(News, id=news_id)

        # Trigger re-analysis
        analyze_article_sentiment.delay(news.id)

        messages.success(request, 'Analysis queued. Please refresh in a moment.')
        return redirect('news_analyser:news_analysis', news_id=news.id)


# ============================================================================
# EXISTING VIEWS (kept for compatibility)
# ============================================================================

@login_required
def all_searches(request):
    """Show all user's past searches"""
    kwds = request.user.profile.searches.all()
    searches = {}
    for kwd in kwds:
        searches[kwd] = kwd.news.all().select_related('source')[:10]

    return render(request, 'news_analyser/all_searches.html', {'kw_link': searches})


@login_required
def past_searches(request):
    """Past searches page"""
    searches = request.user.profile.searches.all().annotate(
        news_count=Count('news')
    ).order_by('-create_date')

    return render(request, 'news_analyser/past_searches.html', {'searches': searches})


@csrf_exempt
def get_content(request, news_id):
    """Fetch full article content"""
    if request.method == 'POST':
        news = get_object_or_404(News, id=news_id)
        content = asyncio.run(news.get_content())

        news.content = content.get('content', '')
        news.save()

        return JsonResponse({
            'message': 'Content fetched successfully',
            'content': content
        })

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def remove_content(request, news_id):
    """Remove article content"""
    news = get_object_or_404(News, id=news_id)
    news.content = None
    news.save()

    return JsonResponse({'message': 'Content removed successfully'})


@login_required
def user_settings(request):
    """User settings page"""
    user_profile = request.user.profile

    if request.method == 'POST':
        form = UserSettingsForm(request.POST)
        if form.is_valid():
            user_profile.preferences['gemini_api_key'] = form.cleaned_data['gemini_api_key']
            user_profile.save()
            messages.success(request, 'Your settings have been saved.')
            return redirect('news_analyser:user_settings')
    else:
        form = UserSettingsForm(
            initial={'gemini_api_key': user_profile.preferences.get('gemini_api_key', '')}
        )

    return render(request, 'news_analyser/user_settings.html', {'form': form})


@login_required
def add_stocks(request):
    """Add stocks to watchlist"""
    if request.method == 'POST':
        selected_stocks = request.POST.getlist('stocks')
        request.user.profile.stocks.set(selected_stocks)
        messages.success(request, 'Your stock portfolio has been updated.')
        return redirect('news_analyser:add_stocks')

    stocks = Stock.objects.all().select_related('sector').order_by('symbol')
    user_stocks = request.user.profile.stocks.values_list('id', flat=True)

    # Group stocks by sector
    sectors = Sector.objects.all()
    stocks_by_sector = {
        sector: stocks.filter(sector=sector)
        for sector in sectors
    }

    context = {
        'stocks': stocks,
        'user_stocks': user_stocks,
        'stocks_by_sector': stocks_by_sector,
    }

    return render(request, 'news_analyser/add_stocks.html', context)


def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            return redirect('news_analyser:dashboard')
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/register.html', {'form': form})


# ============================================================================
# UTILITY VIEWS
# ============================================================================

@login_required
def trigger_scraping(request):
    """Manually trigger news scraping"""
    if request.user.is_staff:
        scrape_all_sources.delay()
        messages.success(request, 'Scraping task queued successfully.')
    else:
        messages.error(request, 'Only staff users can trigger scraping.')

    return redirect('news_analyser:dashboard')


def task_status(request, keyword_id):
    """Check analysis task status"""
    keyword = get_object_or_404(Keyword, id=keyword_id)
    news = keyword.news.all()
    total_news = news.count()
    analysed_news = news.filter(is_analyzed=True).count()

    return JsonResponse({
        'total_news': total_news,
        'analysed_news': analysed_news,
        'progress': (analysed_news / total_news * 100) if total_news > 0 else 0
    })
