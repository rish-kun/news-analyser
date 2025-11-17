import os
import google.generativeai as genai

class GeminiAPI:
    """A client for interacting with the Gemini API."""

    def __init__(self):
        """Initializes the Gemini API client."""
        self.api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)

    def get_sentiment(self, text):
        """
        Analyzes the sentiment of a given text.

        Args:
            text: The text to analyze.

        Returns:
            A dictionary containing the sentiment analysis results.
        """
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(text)
        return response.text
