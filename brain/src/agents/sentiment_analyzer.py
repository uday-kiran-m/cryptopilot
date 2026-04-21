import random
from datetime import datetime
from ..schema.models import SentimentResult


class SentimentAnalyzer:
    """
    Sentiment analyzer stub.
    Returns a sentiment score from 0.0 to 1.0:
    - 0.0 = extreme fear
    - 0.5 = neutral
    - 1.0 = extreme greed
    
    Currently returns a random value for testing.
    Can be upgraded to use real news APIs (CryptoPanic, CoinGecko, etc.)
    """

    def __init__(self, use_stub: bool = True, fixed_score: float = 0.5):
        self.use_stub = use_stub
        self.fixed_score = fixed_score

    def analyze(self, symbol: str) -> SentimentResult:
        """
        Analyze sentiment for a given symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            
        Returns:
            SentimentResult with score from 0.0 to 1.0
        """
        if self.use_stub:
            score = self.fixed_score
        else:
            score = self._fetch_sentiment(symbol)

        return SentimentResult(
            symbol=symbol,
            score=score,
            timestamp=datetime.now(),
            source="stub" if self.use_stub else "news_api"
        )

    def get_score(self, symbol: str) -> float:
        """Return just the score float for convenience"""
        return self.analyze(symbol).score

    def _fetch_sentiment(self, symbol: str) -> float:
        """
        Placeholder for real sentiment fetching.
        TODO: Integrate with CryptoPanic API, CoinDesk, or other news sources.
        """
        return 0.5


def create_sentiment_analyzer(config: dict = None) -> SentimentAnalyzer:
    """Factory function to create sentiment analyzer with config"""
    config = config or {}
    return SentimentAnalyzer(
        use_stub=config.get("use_stub", True),
        fixed_score=config.get("fixed_score", 0.5)
    )
