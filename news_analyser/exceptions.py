"""
Custom exceptions for the News Analyser application.

This module defines domain-specific exceptions for better error handling
and debugging throughout the application.
"""


class NewsAnalyserException(Exception):
    """Base exception for all News Analyser errors."""
    pass


class GeminiAPIError(NewsAnalyserException):
    """Raised when Gemini API calls fail."""
    pass


class GeminiRateLimitError(GeminiAPIError):
    """Raised when Gemini API rate limit is exceeded."""
    pass


class GeminiAuthenticationError(GeminiAPIError):
    """Raised when Gemini API authentication fails."""
    pass


class RSSFeedError(NewsAnalyserException):
    """Raised when RSS feed parsing fails."""
    pass


class ContentExtractionError(NewsAnalyserException):
    """Raised when article content extraction fails."""
    pass


class NewsParsingError(NewsAnalyserException):
    """Raised when news parsing fails."""
    pass


class InvalidSentimentScoreError(NewsAnalyserException):
    """Raised when sentiment score is invalid or out of range."""
    pass
