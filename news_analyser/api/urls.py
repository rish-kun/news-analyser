"""
API URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NewsViewSet, SentimentViewSet, StockViewSet,
    SectorViewSet, UserProfileViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'news', NewsViewSet, basename='news')
router.register(r'sentiment', SentimentViewSet, basename='sentiment')
router.register(r'stocks', StockViewSet, basename='stock')
router.register(r'sectors', SectorViewSet, basename='sector')
router.register(r'profiles', UserProfileViewSet, basename='profile')

urlpatterns = [
    path('', include(router.urls)),
]
