"""
Utility functions for sentiment analysis including ticker recognition
"""

import os
import re
import csv
import logging
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher
from pathlib import Path
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TickerRecognizer:
    """Recognizes stock tickers from text using NSE ticker list"""

    def __init__(self, ticker_csv_path: Optional[str] = None):
        """
        Initialize ticker recognizer

        Args:
            ticker_csv_path: Path to NSE ticker CSV file
        """
        if ticker_csv_path is None:
            # Default path relative to project root
            ticker_csv_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'Ticker_List_NSE_India.csv'
            )

        self.ticker_csv_path = ticker_csv_path
        self.ticker_data = {}
        self.company_variations = {}
        self._load_ticker_data()

    def _load_ticker_data(self):
        """Load and process NSE ticker data"""
        cache_key = 'ticker_data_cache'
        cached_data = cache.get(cache_key)

        if cached_data:
            self.ticker_data = cached_data['ticker_data']
            self.company_variations = cached_data['company_variations']
            logger.info("Loaded ticker data from cache")
            return

        try:
            with open(self.ticker_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row.get('Symbol', '').strip()
                    company_name = row.get('Company Name', '').strip()
                    industry = row.get('Industry', '').strip()

                    if symbol and company_name:
                        self.ticker_data[symbol] = {
                            'name': company_name,
                            'industry': industry,
                            'symbol': symbol
                        }

                        # Create variations for fuzzy matching
                        self._add_company_variations(symbol, company_name)

            # Cache the data for 1 hour
            cache.set(cache_key, {
                'ticker_data': self.ticker_data,
                'company_variations': self.company_variations
            }, 3600)

            logger.info(f"Loaded {len(self.ticker_data)} tickers from {self.ticker_csv_path}")

        except FileNotFoundError:
            logger.error(f"Ticker CSV file not found: {self.ticker_csv_path}")
        except Exception as e:
            logger.error(f"Error loading ticker data: {e}")

    def _add_company_variations(self, symbol: str, company_name: str):
        """Create searchable variations of company names"""
        # Original name
        self.company_variations[company_name.lower()] = symbol

        # Remove common suffixes
        name_clean = re.sub(r'\s+(ltd|limited|pvt|private|corporation|corp|inc|company)\s*$',
                           '', company_name, flags=re.IGNORECASE).strip()
        if name_clean.lower() != company_name.lower():
            self.company_variations[name_clean.lower()] = symbol

        # Abbreviations (first letters of each word)
        words = name_clean.split()
        if len(words) > 1:
            abbreviation = ''.join([w[0] for w in words if w])
            self.company_variations[abbreviation.lower()] = symbol

    def find_tickers_in_text(self, text: str, threshold: float = 0.85) -> List[Dict]:
        """
        Find all mentioned tickers in text

        Args:
            text: Text to search for tickers
            threshold: Similarity threshold for fuzzy matching (0-1)

        Returns:
            List of dictionaries containing ticker information
        """
        found_tickers = []
        text_lower = text.lower()

        # Direct symbol matching (e.g., RELIANCE, TCS, INFY)
        words = re.findall(r'\b[A-Z]{2,10}\b', text)
        for word in words:
            if word in self.ticker_data:
                found_tickers.append({
                    'symbol': word,
                    'name': self.ticker_data[word]['name'],
                    'industry': self.ticker_data[word]['industry'],
                    'match_type': 'exact_symbol'
                })

        # Company name matching
        for variation, symbol in self.company_variations.items():
            if variation in text_lower:
                if symbol not in [t['symbol'] for t in found_tickers]:
                    found_tickers.append({
                        'symbol': symbol,
                        'name': self.ticker_data[symbol]['name'],
                        'industry': self.ticker_data[symbol]['industry'],
                        'match_type': 'company_name'
                    })

        # Fuzzy matching for company names
        text_words = text_lower.split()
        for i in range(len(text_words)):
            for j in range(i + 1, min(i + 5, len(text_words) + 1)):
                phrase = ' '.join(text_words[i:j])
                if len(phrase) < 4:
                    continue

                for company_name, symbol in self.company_variations.items():
                    if len(company_name) < 4:
                        continue

                    similarity = self._similarity(phrase, company_name)
                    if similarity >= threshold:
                        if symbol not in [t['symbol'] for t in found_tickers]:
                            found_tickers.append({
                                'symbol': symbol,
                                'name': self.ticker_data[symbol]['name'],
                                'industry': self.ticker_data[symbol]['industry'],
                                'match_type': 'fuzzy_match',
                                'similarity': similarity
                            })

        return found_tickers

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a, b).ratio()

    def get_ticker_info(self, symbol: str) -> Optional[Dict]:
        """Get information for a specific ticker symbol"""
        return self.ticker_data.get(symbol)


def load_ticker_data(csv_path: Optional[str] = None) -> Dict:
    """
    Load ticker data from CSV file

    Args:
        csv_path: Path to ticker CSV file

    Returns:
        Dictionary mapping symbols to ticker information
    """
    recognizer = TickerRecognizer(csv_path)
    return recognizer.ticker_data


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract named entities from text (companies, people, locations)

    Args:
        text: Text to extract entities from

    Returns:
        Dictionary with entity types as keys and lists of entities as values
    """
    # Placeholder for entity extraction
    # In production, use spaCy or similar NLP library
    entities = {
        'companies': [],
        'people': [],
        'locations': [],
        'organizations': []
    }

    # Simple regex-based extraction as fallback
    # Capitalized words/phrases (basic heuristic)
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)

    # This is a very basic implementation
    # In production, use a proper NER model
    for entity in capitalized:
        if len(entity.split()) <= 3:
            entities['organizations'].append(entity)

    return entities


def calculate_confidence(scores: Dict[str, float]) -> float:
    """
    Calculate confidence score based on agreement between models

    Args:
        scores: Dictionary of model names to sentiment scores

    Returns:
        Confidence score (0-1)
    """
    if not scores:
        return 0.0

    valid_scores = [s for s in scores.values() if s is not None]
    if len(valid_scores) < 2:
        return 0.5

    # Calculate variance
    mean_score = sum(valid_scores) / len(valid_scores)
    variance = sum((s - mean_score) ** 2 for s in valid_scores) / len(valid_scores)

    # Low variance = high confidence
    # Normalize variance to 0-1 range (assuming max variance is 1.0)
    confidence = 1.0 - min(variance, 1.0)

    return confidence
