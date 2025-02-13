from django.shortcuts import render
from django.views import View
from .rss import check_keywords
from .models import News, Keyword
# Create your views here.
# create kwd_news dict 


class SearchView(View):
    def get(self, request):
        return render(request, "news_analyser/search.html")
    def post(self, request):
        kwds = request.POST.get("keyword").split(",")
        news = check_keywords(kwds) 
        kwd_link ={}
        print(news)
        for k, n in news.items():
            k_obj = Keyword.objects.create(name=k)
            for i in n:
                n_obj = News.parse_news(i, k_obj)
                kwd_link[k] = [n_obj] + kwd_link.get(k, [])
            
        return render(request, "news_analyser/result.html", {"kw_link":kwd_link})
        

def all_searches(request):
    kwds = Keyword.objects.all()
    searches = {}
    for kwd in kwds:
        searches[kwd] = kwd.news.all()

    return render(request, "news_analyser/all_searches.html", {"all_searches":searches})