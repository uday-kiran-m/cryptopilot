import feedparser
from datetime import datetime
from typing import Optional

import httpx

from src.core import get_logger
from src.core.config import settings
from src.core.models import NewsArticle, SentimentAnalysis

logger = get_logger("news_client")

COINDESK_RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/"

_sentiment_keywords_positive = [
    "bullish", "surge", "rally", "soar", "gain", "rise", "up", "growth", "adoption",
    "breakout", "all-time-high", " ATH ", "high", "buy", "upgrade", "partnership",
    "launch", "innovation", "success", "profit", "record", "boom", "optimism"
]

_sentiment_keywords_negative = [
    "bearish", "crash", "plunge", "drop", "fall", "decline", "sell", "down", "loss",
    "hack", "scam", "fraud", "ban", "regulation", "risk", "warning", "investigation",
    "fear", "uncertainty", "dump", "correction", "breakdown", "low", "bankruptcy"
]


def _analyze_sentiment(text: str) -> tuple[float, str]:
    """Simple keyword-based sentiment analysis"""
    text_lower = text.lower()
    positive_count = sum(1 for kw in _sentiment_keywords_positive if kw in text_lower)
    negative_count = sum(1 for kw in _sentiment_keywords_negative if kw in text_lower)
    
    total = positive_count + negative_count
    if total == 0:
        return 0.0, "neutral"
    
    score = (positive_count - negative_count) / total
    score = max(-1.0, min(1.0, score))
    
    if score > 0.2:
        label = "bullish"
    elif score < -0.2:
        label = "bearish"
    else:
        label = "neutral"
    
    return score, label


class NewsClient:
    def __init__(self):
        self.cryptopanic_api_key = settings.cryptopanic_api_key
        self.cryptopanic_base_url = "https://cryptopanic.com/api/v1/posts/"

    async def fetch_cryptopanic_news(
        self,
        currencies: Optional[list[str]] = None,
        filter_kind: str = "news",
        limit: int = 50,
    ) -> list[NewsArticle]:
        """Fetch news from CryptoPanic API"""
        if not self.cryptopanic_api_key:
            logger.warning("CryptoPanic API key not configured, skipping")
            return []

        try:
            params = {
                "auth_token": self.cryptopanic_api_key,
                "filter": filter_kind,
                "limit": limit,
            }
            if currencies:
                params["currencies"] = ",".join(currencies)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.cryptopanic_base_url, params=params)
                response.raise_for_status()
                data = response.json()

            articles = []
            for result in data.get("results", []):
                title = result.get("title", "")
                sentiment_score, sentiment_label = _analyze_sentiment(title)

                votes = result.get("votes", {})
                currencies_data = result.get("currencies", [])

                article = NewsArticle(
                    title=title,
                    url=result.get("url", ""),
                    source=result.get("domain", ""),
                    published_at=datetime.fromisoformat(
                        result.get("published_at", "").replace("Z", "+00:00")
                    ),
                    sentiment_score=sentiment_score,
                    sentiment_label=sentiment_label,
                    affected_currencies=[
                        c.get("code", "") for c in currencies_data if c.get("code")
                    ],
                    votes_positive=votes.get("positive", 0),
                    votes_negative=votes.get("negative", 0),
                )
                articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from CryptoPanic")
            return articles

        except Exception as e:
            logger.error(f"Error fetching CryptoPanic news: {e}")
            return []

    def fetch_coindesk_rss(self, limit: int = 20) -> list[NewsArticle]:
        """Fetch latest news from CoinDesk RSS feed"""
        try:
            feed = feedparser.parse(COINDESK_RSS_URL)

            articles = []
            for entry in feed.entries[:limit]:
                title = entry.get("title", "")
                sentiment_score, sentiment_label = _analyze_sentiment(title)

                published = datetime.now()
                if entry.get("published_parsed"):
                    from time import mktime

                    published = datetime.fromtimestamp(
                        mktime(entry.published_parsed)
                    )

                article = NewsArticle(
                    title=title,
                    url=entry.get("link", ""),
                    source="coindesk.com",
                    published_at=published,
                    sentiment_score=sentiment_score,
                    sentiment_label=sentiment_label,
                )
                articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from CoinDesk RSS")
            return articles

        except Exception as e:
            logger.error(f"Error fetching CoinDesk RSS: {e}")
            return []

    async def get_sentiment_analysis(
        self, symbol: str, hours: int = 24
    ) -> SentimentAnalysis:
        """Aggregate sentiment from all sources for a symbol"""
        base, _ = settings.get_symbol_display(symbol)
        currencies = [base, symbol.replace("USDT", "")]

        cryptopanic_articles = await self.fetch_cryptopanic_news(currencies=currencies)
        coindesk_articles = self.fetch_coindesk_rss()

        all_articles = cryptopanic_articles + coindesk_articles

        bullish = [a for a in all_articles if a.sentiment_label == "bullish"]
        bearish = [a for a in all_articles if a.sentiment_label == "bearish"]
        neutral = [a for a in all_articles if a.sentiment_label == "neutral"]

        if not all_articles:
            return SentimentAnalysis(
                symbol=symbol,
                timestamp=datetime.now(),
                overall_score=0.0,
                articles=[],
            )

        total_votes = sum(
            a.votes_positive + a.votes_negative for a in cryptopanic_articles
        )
        if total_votes > 0:
            weighted = sum(
                a.sentiment_score * (a.votes_positive + a.votes_negative)
                for a in cryptopanic_articles
            ) / total_votes
        else:
            weighted = sum(a.sentiment_score for a in all_articles) / len(all_articles)

        return SentimentAnalysis(
            symbol=symbol,
            timestamp=datetime.now(),
            overall_score=weighted,
            bullish_count=len(bullish),
            bearish_count=len(bearish),
            neutral_count=len(neutral),
            articles=all_articles,
            weighted_sentiment=weighted,
        )


news_client = NewsClient()
