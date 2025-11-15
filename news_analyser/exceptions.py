class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors."""
    pass

class RSSFeedError(Exception):
    """Custom exception for RSS feed parsing errors."""
    pass

class ContentExtractionError(Exception):
    """Custom exception for errors during content extraction."""
    pass
