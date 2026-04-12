"""News page with sentiment analysis."""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

from src.dashboard.components.cards import NewsCard
from src.dashboard.components.charts import SentimentChart
from src.dashboard.shared.utils import sentiment_badge, time_ago


def generate_stub_news(symbol: str = "BTC") -> List[Dict[str, Any]]:
    """Generate realistic stub news articles."""
    news_templates = [
        {
            'title': f'{symbol} Surges as Institutional Interest Grows',
            'summary': 'Major financial institutions are increasingly allocating to cryptocurrencies, with analysts predicting continued momentum.',
            'source': 'CoinDesk',
            'sentiment': 'bullish',
        },
        {
            'title': f'New {symbol} ETF Sees Record Inflows',
            'summary': 'The latest exchange-traded fund tracking cryptocurrency prices recorded its highest daily inflows since launch.',
            'source': 'Bloomberg Crypto',
            'sentiment': 'bullish',
        },
        {
            'title': f'{symbol} Price Analysis: What to Expect This Week',
            'summary': 'Technical analysts are divided on short-term direction, with key resistance levels approaching.',
            'source': 'CryptoSlate',
            'sentiment': 'neutral',
        },
        {
            'title': f'Regulatory Uncertainty Impacts {symbol} Markets',
            'summary': 'Recent statements from regulatory bodies have created mixed signals for the cryptocurrency market.',
            'source': 'The Block',
            'sentiment': 'bearish',
        },
        {
            'title': f'{symbol} Network Upgrade Successfully Deployed',
            'summary': 'The long-awaited protocol improvement has been activated, improving transaction speeds and reducing fees.',
            'source': 'Decrypt',
            'sentiment': 'bullish',
        },
        {
            'title': f'Market Watch: {symbol} Consolidates After Rally',
            'summary': 'After a significant price increase, traders are closely watching key support levels for continuation.',
            'source': 'CoinTelegraph',
            'sentiment': 'neutral',
        },
        {
            'title': f'{symbol} On-Chain Metrics Show Strong Network Health',
            'summary': 'Active addresses and transaction volumes remain elevated, indicating sustained user engagement.',
            'source': 'Glassnode',
            'sentiment': 'bullish',
        },
        {
            'title': f'Crypto Market Cap Approaches $3 Trillion Milestone',
            'summary': 'Combined cryptocurrency market capitalization has risen significantly as risk appetite increases.',
            'source': 'CoinMarketCap',
            'sentiment': 'bullish',
        },
    ]
    
    articles = []
    for i, template in enumerate(news_templates):
        hours_ago = random.randint(1, 48)
        article = {
            **template,
            'published': datetime.now() - timedelta(hours=hours_ago),
            'url': f'https://example.com/article/{i}',
            'sentiment_score': random.uniform(0.3, 0.9) if 'bullish' in template['sentiment'] 
                               else random.uniform(0.1, 0.4) if 'bearish' in template['sentiment']
                               else random.uniform(0.4, 0.6),
        }
        articles.append(article)
    
    return sorted(articles, key=lambda x: x['published'], reverse=True)


def calculate_aggregate_sentiment(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate aggregate sentiment from articles."""
    if not articles:
        return {'bullish': 0.5, 'bearish': 0.3, 'neutral': 0.2}
    
    sentiment_scores = [a.get('sentiment_score', 0.5) for a in articles]
    avg_score = sum(sentiment_scores) / len(sentiment_scores)
    
    return {
        'bullish': avg_score,
        'bearish': 1 - avg_score,
        'neutral': 0.5,
        'average_score': avg_score,
        'article_count': len(articles),
    }


def render_news_page(symbol: str = "BTC", use_stubs: bool = True):
    """Render the news page."""
    st.header("📰 News & Sentiment")
    st.markdown("Latest cryptocurrency news with AI-powered sentiment analysis")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        sentiment_filter = st.selectbox(
            "Filter by Sentiment",
            options=["All", "Bullish", "Bearish", "Neutral"],
            index=0
        )
        
        source_filter = st.selectbox(
            "Filter by Source",
            options=["All Sources", "CoinDesk", "CoinTelegraph", "CryptoSlate", "The Block"],
            index=0
        )
        
        if st.button("🔄 Refresh News", use_container_width=True):
            st.rerun()
    
    with col1:
        articles = generate_stub_news(symbol)
    
    filtered_articles = articles.copy()
    if sentiment_filter != "All":
        filtered_articles = [a for a in filtered_articles 
                            if a.get('sentiment', '').lower() == sentiment_filter.lower()]
    
    if source_filter != "All Sources":
        filtered_articles = [a for a in filtered_articles 
                            if a.get('source', '').lower() == source_filter.lower()]
    
    aggregate = calculate_aggregate_sentiment(filtered_articles)
    
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Articles", len(filtered_articles))
    with col2:
        st.metric("Avg Sentiment", f"{aggregate['average_score']:.0%}", 
                  delta="Bullish" if aggregate['average_score'] > 0.55 else "Bearish")
    with col3:
        bullish_count = len([a for a in filtered_articles if 'bullish' in a.get('sentiment', '')])
        st.metric("Bullish", bullish_count)
    with col4:
        bearish_count = len([a for a in filtered_articles if 'bearish' in a.get('sentiment', '')])
        st.metric("Bearish", bearish_count)
    
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### Sentiment Overview")
        sentiment_data = {
            'Bullish': aggregate['bullish'],
            'Neutral': aggregate['neutral'],
            'Bearish': aggregate['bearish'],
        }
        SentimentChart.render_bars(sentiment_data, title="")
        
        st.markdown("### Recent Sentiment Trend")
        sentiment_history = []
        for i in range(7):
            sentiment_history.append({
                'timestamp': (datetime.now() - timedelta(days=6-i)).strftime('%Y-%m-%d'),
                'score': random.uniform(0.4, 0.7),
            })
        SentimentChart.render_timeline(sentiment_history, title="")
    
    with col1:
        st.markdown("### Latest Headlines")
        for article in filtered_articles:
            NewsCard.render(article)
