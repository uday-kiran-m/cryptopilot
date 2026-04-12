from datetime import datetime
from typing import Optional

from crewai import Agent
from crewai.tools import BaseTool

from src.core import get_logger
from src.core.models import NewsArticle, SentimentAnalysis
from src.tools.news_client import news_client

logger = get_logger("sentiment_agent")


class CryptoPanicTool(BaseTool):
    name: str = "cryptopanic_news_fetcher"
    description: str = "Fetches cryptocurrency news from CryptoPanic API"

    async def _arun(self, currencies: list[str], limit: int = 50):
        try:
            articles = await news_client.fetch_cryptopanic_news(currencies=currencies, limit=limit)
            return articles
        except Exception as e:
            logger.error(f"Error in CryptoPanicTool: {e}")
            return []


class CoinDeskRSSTool(BaseTool):
    name: str = "coindesk_rss_fetcher"
    description: str = "Fetches latest news from CoinDesk RSS feed"

    async def _arun(self, limit: int = 20):
        try:
            articles = news_client.fetch_coindesk_rss(limit=limit)
            return articles
        except Exception as e:
            logger.error(f"Error in CoinDeskRSSTool: {e}")
            return []


class SentimentAnalysisTool(BaseTool):
    name: str = "sentiment_analyzer"
    description: str = "Analyzes sentiment from news articles"

    async def _arun(self, symbol: str):
        try:
            analysis = await news_client.get_sentiment_analysis(symbol=symbol)
            return analysis
        except Exception as e:
            logger.error(f"Error in SentimentAnalysisTool: {e}")
            return SentimentAnalysis(symbol=symbol, timestamp=datetime.now())


def create_sentiment_agent() -> Agent:
    """Create the sentiment analysis agent"""
    return Agent(
        role="Sentiment Analyst",
        goal="Analyze market sentiment from news sources to gauge bullishness/bearishness",
        backstory="""You are a sentiment analysis expert specializing in cryptocurrency markets.
        You analyze news articles, social media trends, and market commentary to determine
        overall market sentiment. Your insights help trading decisions by understanding
        the emotional state of the market.""",
        tools=[CryptoPanicTool(), CoinDeskRSSTool(), SentimentAnalysisTool()],
        verbose=True,
        allow_delegation=False,
    )


async def analyze_symbol_sentiment(symbol: str) -> SentimentAnalysis:
    """Analyze sentiment for a symbol from all news sources"""
    base, _ = symbol.replace("USDT", ""), "USDT"
    currencies = [base, symbol.replace("USDT", "")]

    sentiment = await news_client.get_sentiment_analysis(symbol, hours=24)

    logger.info(
        f"Sentiment analysis for {symbol}: score={sentiment.overall_score:.2f}, "
        f"bullish={sentiment.bullish_count}, bearish={sentiment.bearish_count}"
    )

    return sentiment


def interpret_sentiment_score(score: float) -> tuple[str, str]:
    """Interpret sentiment score into label and recommendation"""
    if score >= 0.3:
        return "Strong Bullish", "Consider BUY signals more seriously"
    elif score >= 0.1:
        return "Mildly Bullish", "Slight preference for BUY signals"
    elif score >= -0.1:
        return "Neutral", "No strong bias from sentiment"
    elif score >= -0.3:
        return "Mildly Bearish", "Slight preference for SELL signals"
    else:
        return "Strong Bearish", "Consider SELL signals more seriously"


def get_sentiment_weight(score: float) -> float:
    """Convert sentiment score to a weight (0-1)"""
    return min(1.0, abs(score) + 0.3)
