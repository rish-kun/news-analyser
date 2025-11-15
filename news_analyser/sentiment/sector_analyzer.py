"""
Sector-based sentiment analysis for Indian stock market
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.db.models import Avg, Count, Q
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SectorSentimentAnalyzer:
    """
    Analyzes sentiment trends across different market sectors
    """

    # Indian stock market sectors
    SECTORS = {
        'banking': ['bank', 'hdfc', 'icici', 'sbi', 'axis', 'kotak', 'finance', 'financial'],
        'it': ['tcs', 'infosys', 'wipro', 'hcl', 'tech mahindra', 'information technology', 'software'],
        'pharma': ['sun pharma', 'dr reddy', 'cipla', 'lupin', 'pharmaceutical', 'healthcare'],
        'auto': ['maruti', 'tata motors', 'mahindra', 'bajaj auto', 'automobile', 'automotive'],
        'fmcg': ['hindustan unilever', 'itc', 'nestle', 'britannia', 'consumer goods', 'fmcg'],
        'energy': ['reliance', 'ongc', 'ntpc', 'power grid', 'oil', 'gas', 'energy', 'petroleum'],
        'metals': ['tata steel', 'hindalco', 'vedanta', 'jswsteel', 'steel', 'metal', 'mining'],
        'telecom': ['bharti airtel', 'vodafone', 'jio', 'telecom', 'telecommunications'],
        'realty': ['dlf', 'godrej properties', 'real estate', 'realty', 'construction'],
        'infrastructure': ['larsen toubro', 'infrastructure', 'construction', 'engineering']
    }

    def __init__(self):
        """Initialize sector sentiment analyzer"""
        self.sector_keywords = self.SECTORS

    def identify_sectors(self, text: str) -> List[str]:
        """
        Identify which sectors are mentioned in the text

        Args:
            text: Text to analyze

        Returns:
            List of identified sector names
        """
        text_lower = text.lower()
        identified_sectors = []

        for sector, keywords in self.sector_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if sector not in identified_sectors:
                        identified_sectors.append(sector)
                    break

        return identified_sectors

    def get_sector_sentiment(self, sector_name: str, hours: int = 24) -> Optional[Dict]:
        """
        Get aggregate sentiment for a sector over specified time period

        Args:
            sector_name: Name of the sector
            hours: Number of hours to look back

        Returns:
            Dictionary with sector sentiment statistics
        """
        from news_analyser.models import SentimentScore, Sector

        cache_key = f'sector_sentiment_{sector_name}_{hours}h'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            sector = Sector.objects.filter(name__iexact=sector_name).first()
            if not sector:
                return None

            # Get sentiment scores from the last N hours
            cutoff_time = datetime.now() - timedelta(hours=hours)

            scores = SentimentScore.objects.filter(
                sector=sector,
                created_at__gte=cutoff_time
            )

            if not scores.exists():
                return None

            # Calculate statistics
            stats = scores.aggregate(
                avg_sentiment=Avg('sentiment_score'),
                count=Count('id')
            )

            # Get sentiment distribution
            very_positive = scores.filter(sentiment_label='very_positive').count()
            positive = scores.filter(sentiment_label='positive').count()
            neutral = scores.filter(sentiment_label='neutral').count()
            negative = scores.filter(sentiment_label='negative').count()
            very_negative = scores.filter(sentiment_label='very_negative').count()

            result = {
                'sector': sector_name,
                'average_sentiment': stats['avg_sentiment'],
                'article_count': stats['count'],
                'distribution': {
                    'very_positive': very_positive,
                    'positive': positive,
                    'neutral': neutral,
                    'negative': negative,
                    'very_negative': very_negative
                },
                'time_period_hours': hours,
                'timestamp': datetime.now().isoformat()
            }

            # Cache for 5 minutes
            cache.set(cache_key, result, 300)

            return result

        except Exception as e:
            logger.error(f"Error calculating sector sentiment for {sector_name}: {e}")
            return None

    def get_all_sectors_sentiment(self, hours: int = 24) -> Dict[str, Dict]:
        """
        Get sentiment for all sectors

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary mapping sector names to sentiment data
        """
        from news_analyser.models import Sector

        sectors = Sector.objects.all()
        results = {}

        for sector in sectors:
            sentiment = self.get_sector_sentiment(sector.name, hours)
            if sentiment:
                results[sector.name] = sentiment

        return results

    def get_sector_rotation_signals(self, hours: int = 24) -> List[Dict]:
        """
        Identify potential sector rotation based on sentiment changes

        Args:
            hours: Number of hours to analyze

        Returns:
            List of sectors with significant sentiment changes
        """
        from news_analyser.models import SentimentScore, Sector
        from django.db.models import Avg

        cutoff_time = datetime.now() - timedelta(hours=hours)
        midpoint_time = datetime.now() - timedelta(hours=hours/2)

        rotation_signals = []

        for sector_name in self.sector_keywords.keys():
            try:
                sector = Sector.objects.filter(name__iexact=sector_name).first()
                if not sector:
                    continue

                # Get sentiment for first half
                first_half = SentimentScore.objects.filter(
                    sector=sector,
                    created_at__gte=cutoff_time,
                    created_at__lt=midpoint_time
                ).aggregate(avg=Avg('sentiment_score'))

                # Get sentiment for second half
                second_half = SentimentScore.objects.filter(
                    sector=sector,
                    created_at__gte=midpoint_time
                ).aggregate(avg=Avg('sentiment_score'))

                if first_half['avg'] is not None and second_half['avg'] is not None:
                    change = second_half['avg'] - first_half['avg']

                    # Significant change threshold
                    if abs(change) > 0.2:
                        signal_type = 'bullish' if change > 0 else 'bearish'

                        rotation_signals.append({
                            'sector': sector_name,
                            'signal': signal_type,
                            'sentiment_change': change,
                            'previous_sentiment': first_half['avg'],
                            'current_sentiment': second_half['avg']
                        })

            except Exception as e:
                logger.error(f"Error calculating rotation signal for {sector_name}: {e}")

        # Sort by absolute change
        rotation_signals.sort(key=lambda x: abs(x['sentiment_change']), reverse=True)

        return rotation_signals

    def get_trending_sectors(self, hours: int = 24, limit: int = 5) -> List[Dict]:
        """
        Get top trending sectors by news volume and sentiment

        Args:
            hours: Number of hours to look back
            limit: Number of top sectors to return

        Returns:
            List of trending sector data
        """
        all_sentiment = self.get_all_sectors_sentiment(hours)

        # Sort by article count and average positive sentiment
        trending = []
        for sector_name, data in all_sentiment.items():
            if data['article_count'] >= 3:  # Minimum threshold
                # Calculate trend score
                trend_score = (
                    data['article_count'] * 0.5 +
                    max(0, data['average_sentiment']) * 50
                )

                trending.append({
                    'sector': sector_name,
                    'trend_score': trend_score,
                    'article_count': data['article_count'],
                    'average_sentiment': data['average_sentiment'],
                    'distribution': data['distribution']
                })

        trending.sort(key=lambda x: x['trend_score'], reverse=True)

        return trending[:limit]

    def get_sector_correlation(self, sector1: str, sector2: str, hours: int = 168) -> Optional[float]:
        """
        Calculate sentiment correlation between two sectors

        Args:
            sector1: First sector name
            sector2: Second sector name
            hours: Time period for analysis (default 1 week)

        Returns:
            Correlation coefficient (-1 to 1) or None if insufficient data
        """
        from news_analyser.models import SentimentScore, Sector
        import numpy as np

        try:
            s1 = Sector.objects.filter(name__iexact=sector1).first()
            s2 = Sector.objects.filter(name__iexact=sector2).first()

            if not s1 or not s2:
                return None

            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Get sentiment scores
            scores1 = list(SentimentScore.objects.filter(
                sector=s1,
                created_at__gte=cutoff_time
            ).values_list('sentiment_score', flat=True))

            scores2 = list(SentimentScore.objects.filter(
                sector=s2,
                created_at__gte=cutoff_time
            ).values_list('sentiment_score', flat=True))

            if len(scores1) < 5 or len(scores2) < 5:
                return None

            # Calculate correlation
            correlation = np.corrcoef(scores1[:min(len(scores1), len(scores2))],
                                     scores2[:min(len(scores1), len(scores2))])[0, 1]

            return float(correlation)

        except ImportError:
            logger.error("numpy not installed, correlation calculation unavailable")
            return None
        except Exception as e:
            logger.error(f"Error calculating sector correlation: {e}")
            return None
