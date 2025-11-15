"""
Content deduplication using hashing and similarity detection
"""

import hashlib
import logging
from typing import List, Dict, Optional, Set
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ContentDeduplicator:
    """
    Deduplicates news articles using multiple strategies
    """

    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize deduplicator

        Args:
            similarity_threshold: Threshold for similarity matching (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.cache_ttl = 86400  # 24 hours

    def generate_hash(self, text: str) -> str:
        """
        Generate SHA256 hash of text

        Args:
            text: Text to hash

        Returns:
            Hex digest of hash
        """
        normalized = text.lower().strip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def generate_content_hash(self, title: str, content: str) -> str:
        """
        Generate hash combining title and content

        Args:
            title: Article title
            content: Article content or summary

        Returns:
            Combined hash
        """
        combined = f"{title.lower()}{content.lower()}"
        return self.generate_hash(combined)

    def is_duplicate_by_hash(self, content_hash: str) -> bool:
        """
        Check if content hash exists in cache

        Args:
            content_hash: Hash to check

        Returns:
            True if duplicate, False otherwise
        """
        cache_key = f'content_hash_{content_hash}'
        return cache.get(cache_key) is not None

    def mark_as_seen(self, content_hash: str):
        """
        Mark content hash as seen

        Args:
            content_hash: Hash to mark
        """
        cache_key = f'content_hash_{content_hash}'
        cache.set(cache_key, True, self.cache_ttl)

    def is_duplicate_by_url(self, url: str) -> bool:
        """
        Check if URL has been seen before

        Args:
            url: URL to check

        Returns:
            True if duplicate, False otherwise
        """
        from news_analyser.models import News

        # Check database
        return News.objects.filter(link=url).exists()

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate Jaccard similarity between two texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        # Tokenize
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def find_similar_articles(self, title: str, content: str, max_results: int = 5) -> List[Dict]:
        """
        Find similar articles in database

        Args:
            title: Article title
            content: Article content
            max_results: Maximum number of results to return

        Returns:
            List of similar articles with similarity scores
        """
        from news_analyser.models import News

        similar = []

        # Get recent articles (last 7 days)
        from datetime import timedelta
        from django.utils import timezone

        cutoff_date = timezone.now() - timedelta(days=7)
        recent_articles = News.objects.filter(date__gte=cutoff_date)[:100]

        for article in recent_articles:
            # Calculate title similarity
            title_sim = self.calculate_similarity(title, article.title)

            # Calculate content similarity
            content_sim = self.calculate_similarity(content, article.content_summary)

            # Combined similarity (weighted average)
            overall_sim = 0.6 * title_sim + 0.4 * content_sim

            if overall_sim >= self.similarity_threshold:
                similar.append({
                    'article_id': article.id,
                    'title': article.title,
                    'similarity': overall_sim
                })

        # Sort by similarity
        similar.sort(key=lambda x: x['similarity'], reverse=True)

        return similar[:max_results]

    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove duplicate articles from list

        Args:
            articles: List of article dictionaries

        Returns:
            Deduplicated list of articles
        """
        unique_articles = []
        seen_hashes = set()
        seen_urls = set()

        for article in articles:
            # Check URL
            url = article.get('link', '')
            if url in seen_urls or self.is_duplicate_by_url(url):
                logger.debug(f"Duplicate URL found: {url}")
                continue

            # Check content hash
            content_hash = article.get('content_hash')
            if not content_hash:
                content_hash = self.generate_content_hash(
                    article.get('title', ''),
                    article.get('content_summary', '')
                )
                article['content_hash'] = content_hash

            if content_hash in seen_hashes or self.is_duplicate_by_hash(content_hash):
                logger.debug(f"Duplicate content found: {article.get('title', '')}")
                continue

            # Mark as seen
            seen_hashes.add(content_hash)
            seen_urls.add(url)
            self.mark_as_seen(content_hash)

            unique_articles.append(article)

        logger.info(f"Deduplication: {len(articles)} -> {len(unique_articles)} articles")

        return unique_articles

    def generate_simhash(self, text: str, hash_bits: int = 64) -> int:
        """
        Generate SimHash for near-duplicate detection

        Args:
            text: Text to hash
            hash_bits: Number of bits in hash

        Returns:
            SimHash as integer
        """
        # Tokenize
        tokens = text.lower().split()

        # Initialize bit vector
        v = [0] * hash_bits

        for token in tokens:
            # Hash token
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)

            # Update bit vector
            for i in range(hash_bits):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1

        # Generate final hash
        fingerprint = 0
        for i in range(hash_bits):
            if v[i] > 0:
                fingerprint |= (1 << i)

        return fingerprint

    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """
        Calculate Hamming distance between two hashes

        Args:
            hash1: First hash
            hash2: Second hash

        Returns:
            Number of differing bits
        """
        x = hash1 ^ hash2
        distance = 0

        while x:
            distance += 1
            x &= x - 1

        return distance

    def is_near_duplicate(self, text1: str, text2: str, threshold: int = 3) -> bool:
        """
        Check if two texts are near-duplicates using SimHash

        Args:
            text1: First text
            text2: Second text
            threshold: Maximum Hamming distance for near-duplicates

        Returns:
            True if near-duplicates, False otherwise
        """
        hash1 = self.generate_simhash(text1)
        hash2 = self.generate_simhash(text2)

        distance = self.hamming_distance(hash1, hash2)

        return distance <= threshold
