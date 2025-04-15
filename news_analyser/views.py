from django.shortcuts import render
from django.views import View
from .rss import check_keywords
from .models import News, Keyword
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import time
from django.http import JsonResponse
import asyncio


class SearchView(View):
    def get(self, request):
        return render(request, "news_analyser/search.html")

    def post(self, request):
        kwds = request.POST.get("keyword").split(",")
        news = check_keywords(kwds)
        kwd_link = {}
        for k, n in news.items():
            k_obj, created = Keyword.objects.get_or_create(name=k)
            if created:
                k_obj.save()
            for i in n:
                n_obj = News.parse_news(i, k_obj)
                kwd_link[k] = [n_obj] + kwd_link.get(k, [])

        for k, n in kwd_link.items():
            for i in n:
                i.analyse_news()
                print(i.impact_rating)
        return render(request, "news_analyser/result.html", {"kw_link": kwd_link})
# if there are multiple keywords, then the news should be the intersection of the news
# implement asyn


def all_searches(request):
    kwds = Keyword.objects.all()
    searches = {}
    for kwd in kwds:
        searches[kwd] = kwd.news.all()

    return render(request, "news_analyser/result.html", {"kw_link": searches})


def loading(request):
    return render(request, "news_analyser/stock_loading.html")


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
