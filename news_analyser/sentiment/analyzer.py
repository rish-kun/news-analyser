"""
Advanced Sentiment Analyzer with multi-model support
Supports: Gemini, FinBERT, VADER, TextBlob
"""

import os
import logging
import asyncio
import time
from typing import Dict, Optional, List, Tuple
from google import genai
from django.conf import settings

logger = logging.getLogger(__name__)


class AdvancedSentimentAnalyzer:
    """
    Advanced sentiment analyzer using multiple AI models
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize the sentiment analyzer

        Args:
            gemini_api_key: API key for Google Gemini (optional, uses settings if not provided)
        """
        self.gemini_api_key = gemini_api_key or getattr(settings, 'GEMINI_API_KEY', None)
        self.gemini_client = None
        self.finbert_model = None
        self.finbert_tokenizer = None

        # Rate limiting
        self.last_gemini_call = 0
        self.min_call_interval = 1.0  # seconds between calls

        # Initialize models
        self._initialize_gemini()

    def _initialize_gemini(self):
        """Initialize Gemini AI client"""
        if self.gemini_api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
        else:
            logger.warning("No Gemini API key provided")

    def _initialize_finbert(self):
        """Initialize FinBERT model (lazy loading)"""
        if self.finbert_model is None:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification
                import torch

                model_name = "ProsusAI/finbert"
                self.finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.finbert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
                logger.info("FinBERT model loaded successfully")
            except ImportError:
                logger.error("transformers or torch not installed. FinBERT unavailable.")
            except Exception as e:
                logger.error(f"Failed to load FinBERT model: {e}")

    async def analyze_sentiment(self, text: str, title: str = "", use_models: Optional[List[str]] = None) -> Dict:
        """
        Analyze sentiment using multiple models

        Args:
            text: Main content to analyze
            title: Article title
            use_models: List of models to use (default: all available)

        Returns:
            Dictionary containing scores from each model and composite score
        """
        if use_models is None:
            use_models = ['gemini', 'finbert', 'vader', 'textblob']

        results = {
            'gemini_score': None,
            'finbert_score': None,
            'vader_score': None,
            'textblob_score': None,
            'composite_score': 0.0,
            'confidence': 0.0,
            'model_used': 'ensemble',
            'analysis_details': {}
        }

        # Combine title and text for analysis
        full_text = f"{title}. {text}" if title else text

        # Run analyses
        tasks = []

        if 'gemini' in use_models and self.gemini_client:
            tasks.append(self._analyze_with_gemini(full_text))
        else:
            tasks.append(asyncio.sleep(0))  # Placeholder

        if 'vader' in use_models:
            tasks.append(self._analyze_with_vader(full_text))
        else:
            tasks.append(asyncio.sleep(0))

        if 'textblob' in use_models:
            tasks.append(self._analyze_with_textblob(full_text))
        else:
            tasks.append(asyncio.sleep(0))

        # Execute in parallel
        gemini_result, vader_result, textblob_result = await asyncio.gather(*tasks, return_exceptions=True)

        # Process Gemini result
        if isinstance(gemini_result, dict):
            results['gemini_score'] = gemini_result.get('score')
            results['analysis_details']['gemini'] = gemini_result.get('details', {})

        # Process VADER result
        if isinstance(vader_result, dict):
            results['vader_score'] = vader_result.get('score')
            results['analysis_details']['vader'] = vader_result.get('details', {})

        # Process TextBlob result
        if isinstance(textblob_result, dict):
            results['textblob_score'] = textblob_result.get('score')
            results['analysis_details']['textblob'] = textblob_result.get('details', {})

        # FinBERT (synchronous, run separately)
        if 'finbert' in use_models:
            finbert_result = self._analyze_with_finbert_sync(full_text)
            if finbert_result:
                results['finbert_score'] = finbert_result.get('score')
                results['analysis_details']['finbert'] = finbert_result.get('details', {})

        # Calculate composite score
        results['composite_score'] = self._calculate_composite_score(results)
        results['confidence'] = self._calculate_confidence(results)

        return results

    async def _analyze_with_gemini(self, text: str, max_retries: int = 3) -> Dict:
        """
        Analyze sentiment using Google Gemini

        Args:
            text: Text to analyze
            max_retries: Maximum number of retry attempts

        Returns:
            Dictionary with score and details
        """
        if not self.gemini_client:
            return {'score': None, 'details': {'error': 'Gemini client not initialized'}}

        # Rate limiting
        current_time = time.time()
        time_since_last_call = current_time - self.last_gemini_call
        if time_since_last_call < self.min_call_interval:
            await asyncio.sleep(self.min_call_interval - time_since_last_call)

        prompt = self._get_gemini_prompt(text)

        for attempt in range(max_retries):
            try:
                self.last_gemini_call = time.time()

                # Using synchronous call wrapped in async
                response = await asyncio.to_thread(
                    self.gemini_client.models.generate_content,
                    model="gemini-2.0-flash",
                    contents=prompt
                )

                # Parse response
                score = self._parse_gemini_response(response.text)

                return {
                    'score': score,
                    'details': {
                        'raw_response': response.text,
                        'model': 'gemini-2.0-flash'
                    }
                }

            except genai.errors.ClientError as e:
                logger.warning(f"Gemini API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                else:
                    return {'score': None, 'details': {'error': str(e)}}

            except Exception as e:
                logger.error(f"Unexpected error in Gemini analysis: {e}")
                return {'score': None, 'details': {'error': str(e)}}

        return {'score': None, 'details': {'error': 'Max retries exceeded'}}

    def _get_gemini_prompt(self, text: str) -> str:
        """Generate prompt for Gemini API"""
        return f"""You are an expert financial analyst. Analyze the potential impact of the following news on the Indian stock market.

Consider:
- Investor sentiment
- Industry/sector dynamics
- Macroeconomic indicators
- Market reaction likelihood

Rate the impact on a scale from -1 to 1:
-1: Severely negative impact
-0.75: Highly negative impact
-0.5: Moderately negative impact
-0.25: Slightly negative impact
0: No effect
0.25: Slightly positive impact
0.5: Moderately positive impact
0.75: Highly positive impact
1: Extremely positive impact

Provide ONLY a single numerical rating between -1 and 1 as your response, nothing else.

News:
{text[:4000]}
"""

    def _parse_gemini_response(self, response_text: str) -> Optional[float]:
        """Parse Gemini response to extract sentiment score"""
        try:
            # Extract number from response
            import re
            numbers = re.findall(r'-?\d+\.?\d*', response_text)
            if numbers:
                score = float(numbers[0])
                # Clamp to [-1, 1]
                return max(-1.0, min(1.0, score))
        except (ValueError, IndexError):
            logger.error(f"Failed to parse Gemini response: {response_text}")

        return None

    async def _analyze_with_vader(self, text: str) -> Dict:
        """Analyze sentiment using VADER"""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            analyzer = SentimentIntensityAnalyzer()
            scores = analyzer.polarity_scores(text)

            # VADER compound score is already in [-1, 1] range
            return {
                'score': scores['compound'],
                'details': {
                    'positive': scores['pos'],
                    'negative': scores['neg'],
                    'neutral': scores['neu'],
                    'compound': scores['compound']
                }
            }

        except ImportError:
            logger.error("vaderSentiment not installed")
            return {'score': None, 'details': {'error': 'vaderSentiment not available'}}
        except Exception as e:
            logger.error(f"VADER analysis error: {e}")
            return {'score': None, 'details': {'error': str(e)}}

    async def _analyze_with_textblob(self, text: str) -> Dict:
        """Analyze sentiment using TextBlob"""
        try:
            from textblob import TextBlob

            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # Already in [-1, 1]
            subjectivity = blob.sentiment.subjectivity  # [0, 1]

            return {
                'score': polarity,
                'details': {
                    'polarity': polarity,
                    'subjectivity': subjectivity
                }
            }

        except ImportError:
            logger.error("textblob not installed")
            return {'score': None, 'details': {'error': 'textblob not available'}}
        except Exception as e:
            logger.error(f"TextBlob analysis error: {e}")
            return {'score': None, 'details': {'error': str(e)}}

    def _analyze_with_finbert_sync(self, text: str) -> Optional[Dict]:
        """Analyze sentiment using FinBERT (synchronous)"""
        try:
            if self.finbert_model is None:
                self._initialize_finbert()

            if self.finbert_model is None:
                return None

            import torch

            # Tokenize
            inputs = self.finbert_tokenizer(text[:512], return_tensors="pt", truncation=True, padding=True)

            # Get predictions
            with torch.no_grad():
                outputs = self.finbert_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)

            # FinBERT outputs: [positive, negative, neutral]
            scores = predictions[0].tolist()

            # Convert to -1 to 1 scale
            # positive - negative
            sentiment_score = scores[0] - scores[1]

            return {
                'score': sentiment_score,
                'details': {
                    'positive': scores[0],
                    'negative': scores[1],
                    'neutral': scores[2]
                }
            }

        except Exception as e:
            logger.error(f"FinBERT analysis error: {e}")
            return None

    def _calculate_composite_score(self, results: Dict) -> float:
        """
        Calculate weighted composite score from all models

        Args:
            results: Dictionary containing scores from all models

        Returns:
            Composite sentiment score
        """
        # Weights for each model
        weights = {
            'gemini_score': 0.4,  # Highest weight to Gemini (most contextual)
            'finbert_score': 0.3,  # FinBERT is finance-specific
            'vader_score': 0.2,   # VADER is good for social sentiment
            'textblob_score': 0.1  # TextBlob as baseline
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for model, weight in weights.items():
            score = results.get(model)
            if score is not None:
                weighted_sum += score * weight
                total_weight += weight

        if total_weight > 0:
            return weighted_sum / total_weight

        return 0.0

    def _calculate_confidence(self, results: Dict) -> float:
        """Calculate confidence based on model agreement"""
        scores = [
            results.get('gemini_score'),
            results.get('finbert_score'),
            results.get('vader_score'),
            results.get('textblob_score')
        ]

        valid_scores = [s for s in scores if s is not None]

        if len(valid_scores) < 2:
            return 0.5  # Low confidence if only one model

        # Calculate variance
        mean_score = sum(valid_scores) / len(valid_scores)
        variance = sum((s - mean_score) ** 2 for s in valid_scores) / len(valid_scores)

        # Low variance = high confidence
        confidence = 1.0 - min(variance, 1.0)

        return confidence

    @staticmethod
    def get_sentiment_label(score: float) -> str:
        """Convert numerical score to sentiment label"""
        if score <= -0.6:
            return 'very_negative'
        elif score <= -0.2:
            return 'negative'
        elif score <= 0.2:
            return 'neutral'
        elif score <= 0.6:
            return 'positive'
        else:
            return 'very_positive'
