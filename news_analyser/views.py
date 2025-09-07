from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from .rss import check_keywords
from .models import News, Keyword
from .tasks import analyse_news_task
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import asyncio
from django.contrib import messages


def search_result(request, news_id=None):
    kwd = Keyword.objects.get(id=news_id)
    kw_link = {kwd: kwd.news.all()}
    if request.GET.get("pending"):
        messages.info(
            request, "Pending, all news are not analysed yet. Pls reload after a while")
    return render(request, "news_analyser/result.html", {"kw_link": kw_link})


class SearchView(View):

    def get(self, request):
        return render(request, "news_analyser/search.html")

    def post(self, request):
        search_type = request.POST.get("search_type")
        if search_type == "keyword":
            kwds = request.POST.get("keyword").split(",")
        else:
            kwds = request.POST.getlist("stocks")

        news = check_keywords(kwds)
        kwd_link = {}
        k_obj = None
        for k, n in news.items():
            k_obj, created = Keyword.objects.get_or_create(name=k)
            request.user.profile.searches.add(k_obj)
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


def all_searches(request):
    kwds = Keyword.objects.all()
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


class SectorView(View):
    def get(self, request):
        return render(request, "news_analyser/sector.html")

    def post(self, request):
        sector = request.POST.get("sector")
        print(sector)
        return render(request, "news_analyser/sector.html")


class NewsAnalysisView(View):
    def get(self, request, news_id):
        news = News.objects.get(id=news_id)
        return render(request, "news_analyser/news_analysis.html", {"news": news})

    def post(self, request, news_id):
        news = News.objects.get(id=news_id)
        news.analyse_news()
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
