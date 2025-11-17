# Standard library imports
import asyncio

# Django imports
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.decorators.csrf import csrf_exempt

# Local application imports
from .forms import UserRegistrationForm, UserSettingsForm
from .models import News, Keyword, UserProfile, Stock
from .tasks import analyse_news_task
from .utils.rss import check_keywords


@login_required
def search_result(request, news_id=None):
    """Displays the search results for a given keyword."""
    kwd = get_object_or_404(Keyword, id=news_id)
    kw_link = {kwd: kwd.news.all().prefetch_related('source')}
    if request.GET.get("pending"):
        messages.info(
            request, "Analysis is pending for some articles. Please reload after a while.")
    return render(request, "news_analyser/result.html", {"kw_link": kw_link})


class SearchView(LoginRequiredMixin, View):
    """Handles the main search functionality for keywords and stocks."""
    template_name = "news_analyser/search.html"

    def get(self, request, *args, **kwargs):
        """Displays the search form with the user's watchlist."""
        user_stocks = request.user.profile.stocks.all()
        return render(request, self.template_name, {"user_stocks": user_stocks})

    def post(self, request, *args, **kwargs):
        """Processes the search request and initiates news analysis."""
        search_type = request.POST.get("search_type")

        if search_type == "keyword":
            kwds = [k.strip() for k in request.POST.get("keyword", "").split(",") if k.strip()]
        else:
            kwds = request.POST.getlist("stocks")

        if not kwds:
            messages.error(request, "Please enter a keyword or select a stock.")
            return redirect(reverse("news_analyser:search"))

        news_items = check_keywords(kwds)

        k_obj = None
        for k, n_list in news_items.items():
            k_obj, created = Keyword.objects.get_or_create(name=k)
            request.user.profile.searches.add(k_obj)

            for news_data in n_list:
                news_obj = News.parse_news(news_data, k_obj)
                analyse_news_task.delay(news_obj.id)

        if k_obj:
            return redirect(reverse("news_analyser:search_results", args=[k_obj.id]))
        else:
            messages.info(request, "No news found for the given keywords.")
            return redirect(reverse("news_analyser:search"))


@login_required
def all_searches(request):
    """Displays all past searches made by the user."""
    kwds = request.user.profile.searches.all().prefetch_related('news')
    searches = {kwd: kwd.news.all() for kwd in kwds}
    return render(request, "news_analyser/result.html", {"kw_link": searches})


def loading(request, keyword_id):
    """Displays a loading page while news is being analyzed."""
    return render(request, "news_analyser/loading.html", {"keyword_id": keyword_id})


def task_status(request, keyword_id):
    """Returns the status of the news analysis task as JSON."""
    keyword = get_object_or_404(Keyword, id=keyword_id)
    news = keyword.news.all()
    total_news = news.count()
    analysed_news = news.exclude(impact_rating=0).count()
    return JsonResponse({"total_news": total_news, "analysed_news": analysed_news})


class SectorView(LoginRequiredMixin, View):
    """A view for displaying news by sector (placeholder)."""
    def get(self, request):
        return render(request, "news_analyser/sector.html")

    def post(self, request):
        sector = request.POST.get("sector")
        return render(request, "news_analyser/sector.html")


class NewsAnalysisView(LoginRequiredMixin, View):
    """Displays a detailed analysis of a single news article."""
    def get(self, request, news_id):
        news = get_object_or_404(News, id=news_id)
        return render(request, "news_analyser/news_analysis.html", {"news": news})

    def post(self, request, news_id):
        """Initiates a re-analysis of the news article."""
        news = get_object_or_404(News, id=news_id)
        analyse_news_task.delay(news.id)
        messages.success(request, "Re-analysis initiated.")
        return render(request, "news_analyser/news_analysis.html", {"news": news})


@csrf_exempt
def get_content(request, news_id):
    """Fetches the full content of a news article."""
    if request.method == "POST":
        news = get_object_or_404(News, id=news_id)
        asyncio.run(news.get_content())
        return JsonResponse({"message": "Content fetched successfully", "content": news.content})
    return JsonResponse({"error": "Invalid request method."}, status=405)


@csrf_exempt
def remove_content(request, news_id):
    """Removes the fetched content from a news article."""
    if request.method == "POST":
        news = get_object_or_404(News, id=news_id)
        news.content = None
        news.save()
        return JsonResponse({"message": "Content removed successfully"})
    return JsonResponse({"error": "Invalid request method."}, status=405)


def register(request):
    """Handles user registration."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            return redirect('news_analyser:search')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def user_settings(request):
    """Allows users to manage their settings, such as API keys."""
    user_profile = request.user.profile
    if request.method == 'POST':
        form = UserSettingsForm(request.POST)
        if form.is_valid():
            user_profile.preferences['gemini_api_key'] = form.cleaned_data['gemini_api_key']
            user_profile.save()
            messages.success(request, 'Your settings have been saved.')
            return redirect('news_analyser:user_settings')
    else:
        initial_data = {'gemini_api_key': user_profile.preferences.get('gemini_api_key', '')}
        form = UserSettingsForm(initial=initial_data)
    return render(request, 'news_analyser/user_settings.html', {'form': form})


@login_required
def past_searches(request):
    """Displays a list of the user's past searches."""
    searches = request.user.profile.searches.all()
    return render(request, 'news_analyser/past_searches.html', {'searches': searches})


@login_required
def add_stocks(request):
    """Allows users to add or remove stocks from their watchlist."""
    if request.method == 'POST':
        selected_stocks = request.POST.getlist('stocks')
        request.user.profile.stocks.set(selected_stocks)
        messages.success(request, 'Your stock portfolio has been updated.')
        return redirect('news_analyser:add_stocks')

    stocks = Stock.objects.all()
    user_stocks = request.user.profile.stocks.values_list('id', flat=True)
    return render(request, 'news_analyser/add_stocks.html', {'stocks': stocks, 'user_stocks': user_stocks})
