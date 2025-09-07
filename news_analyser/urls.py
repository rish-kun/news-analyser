from django.urls import path
from .views import *
app_name = "news_analyser"
urlpatterns = [
    path("", SearchView.as_view(), name="search"),
    path("search/<int:news_id>/", search_result, name="search_results"),
    path("all_searches/", all_searches, name="all_searches"),
    path("loading/<int:keyword_id>/", loading, name="loading"),
    path("status/<int:keyword_id>/", task_status, name="task_status"),
    path("sector/", SectorView.as_view(), name="sector"),
    path("news_analysis/<int:news_id>/",
         NewsAnalysisView.as_view(), name="news_analysis"),
    path("news_analysis/<int:news_id>/get_content/",
         get_content, name="get_content"),
    path("settings/", user_settings, name="user_settings"),
    path("past_searches/", past_searches, name="past_searches"),
    path("add_stocks/", add_stocks, name="add_stocks"),
]
