from django.urls import path
from .views import *
from .views_enhanced import (
    DashboardView,
    TickerDetailView,
    SectorAnalysisView,
    SectorDetailView,
    NewsAnalysisView as NewsDetailView,
    WatchlistView
)

app_name = "news_analyser"
urlpatterns = [
    # Enhanced frontend views
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("ticker/<str:symbol>/", TickerDetailView.as_view(), name="ticker_detail"),
    path("sectors/", SectorAnalysisView.as_view(), name="sector_analysis"),
    path("sector/<str:sector_name>/", SectorDetailView.as_view(), name="sector_detail"),
    path("news/<int:news_id>/", NewsDetailView.as_view(), name="news_detail"),
    path("watchlist/", WatchlistView.as_view(), name="watchlist"),

    # Original views (maintained for backward compatibility)
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
