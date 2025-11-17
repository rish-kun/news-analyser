class NewsAnalysisError(Exception):
    """Base exception for news analysis errors."""
    pass


class GeminiAPIError(NewsAnalysisError):
    """Exception raised for errors related to the Gemini API."""
    pass


class RSSFeedError(NewsAnalysisError):
    """Exception raised for errors related to RSS feeds."""
    pass
