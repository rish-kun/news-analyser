from django.urls import path
from .views import SearchView, all_searches
app_name="news_analyser"
urlpatterns = [
    path("", SearchView.as_view(), name="search"),
    path("all_searches/", all_searches, name="all_searches"),
]
