from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from .rss import check_keywords
from .models import News, Keyword
from .tasks import analyse_news_task
from .models import News, Keyword, UserProfile, Stock
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import asyncio
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .forms import UserRegistrationForm, UserSettingsForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required


@login_required
def search_result(request, news_id=None):
    kwd = Keyword.objects.get(id=news_id)
    kw_link = {kwd: kwd.news.all()}
    if request.GET.get("pending"):
        messages.info(
            request, "Pending, all news are not analysed yet. Pls reload after a while")
    return render(request, "news_analyser/result.html", {"kw_link": kw_link})


class SearchView(LoginRequiredMixin, View):

    def get(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_stocks = profile.stocks.all()
        return render(request, "news_analyser/search.html", {"user_stocks": user_stocks})

    def post(self, request):
        search_type = request.POST.get("search_type")
        if search_type == "keyword":
            kwds = request.POST.get("keyword").split(",")
        else:
            kwds = request.POST.getlist("stocks")

        search_type = request.POST.get("search_type")
        if search_type == "keyword":
            kwds = request.POST.get("keyword").split(",")
        else:
            kwds = request.POST.getlist("stocks")

        news = check_keywords(kwds)
        kwd_link = {}
        print("news", news)
        k_obj = None
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        for k, n in news.items():
            print("in the loop")
            k_obj, created = Keyword.objects.get_or_create(name=k)
            profile.searches.add(k_obj)
            if created:
                k_obj.save()
            for i in n:
                n_obj = News.parse_news(i, k_obj)
                kwd_link[k] = [n_obj] + kwd_link.get(k, [])

        for k, n in kwd_link.items():
            for i in n:
                analyse_news_task.delay(i.id)
                print(i.impact_rating)

        if k_obj:
            return redirect(reverse("news_analyser:search_results", args=[k_obj.id]))
        else:
            messages.info(request, "No news found for the given keywords.")
            return redirect(reverse("news_analyser:search"))
# if there are multiple keywords, then the news should be the intersection of the news
# implement asyn


@login_required
def all_searches(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    kwds = profile.searches.all()
    searches = {}
    for kwd in kwds:
        searches[kwd] = kwd.news.all()
    return render(request, "news_analyser/result.html", {"kw_link": searches})


def loading(request, keyword_id):
    return render(request, "news_analyser/loading.html", {"keyword_id": keyword_id})


def task_status(request, keyword_id):
    keyword = Keyword.objects.get(id=keyword_id)
    news = keyword.news.all()
    total_news = news.count()
    analysed_news = news.exclude(impact_rating=0).count()
    return JsonResponse({"total_news": total_news, "analysed_news": analysed_news})


class SectorView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "news_analyser/sector.html")

    def post(self, request):
        sector = request.POST.get("sector")
        print(sector)
        return render(request, "news_analyser/sector.html")


class NewsAnalysisView(LoginRequiredMixin, View):
    def get(self, request, news_id):
        news = News.objects.get(id=news_id)
        return render(request, "news_analyser/news_analysis.html", {"news": news})

    def post(self, request, news_id):
        news = News.objects.get(id=news_id)
        analyse_news_task.delay(news.id)
        return render(request, "news_analyser/news_analysis.html", {"news": news})


@csrf_exempt
def get_content(request, news_id):
    if request.method == "POST":
        news = News.objects.get(id=news_id)
        content = asyncio.run(news.get_content())
        print(content['content'])
        news.content = content['content']
        news.save()
        return JsonResponse({"message": "Content fetched successfully", "content": content})
    else:
        return render(request, "news_analyser/news_analysis.html", {"news": news})


def remove_content(request, news_id):
    news = News.objects.get(id=news_id)
    news.content = None
    news.save()
    return JsonResponse({"message": "Content removed successfully"})


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            return redirect('news_analyser:search')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def user_settings(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserSettingsForm(request.POST)
        if form.is_valid():
            user_profile.preferences['gemini_api_key'] = form.cleaned_data['gemini_api_key']
            user_profile.save()
            messages.success(request, 'Your settings have been saved.')
            return redirect('news_analyser:user_settings')
    else:
        form = UserSettingsForm(
            initial={'gemini_api_key': user_profile.preferences.get('gemini_api_key', '')})
    return render(request, 'news_analyser/user_settings.html', {'form': form})


@login_required
def past_searches(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    searches = profile.searches.all()
    return render(request, 'news_analyser/past_searches.html', {'searches': searches})


@login_required
def add_stocks(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        selected_stocks = request.POST.getlist('stocks')
        profile.stocks.set(selected_stocks)
        messages.success(request, 'Your stock portfolio has been updated.')
        return redirect('news_analyser:add_stocks')

    stocks = Stock.objects.all()
    user_stocks = profile.stocks.values_list('id', flat=True)
    return render(request, 'news_analyser/add_stocks.html', {'stocks': stocks, 'user_stocks': user_stocks})
