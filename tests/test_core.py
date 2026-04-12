import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.core.models import (
    TradeAction,
    OHLCVData,
    TechnicalIndicators,
    SentimentAnalysis,
    TradeSignal,
    Portfolio,
    PortfolioPosition,
)


class TestModels:
    """Test Pydantic data models"""

    def test_ohlcv_data(self):
        ohlcv = OHLCVData(
            timestamp=datetime.now(),
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0,
        )
        assert ohlcv.open == 50000.0
        assert ohlcv.close == 50500.0

    def test_trade_signal(self):
        signal = TradeSignal(
            symbol="BTCUSDT",
            action=TradeAction.BUY,
            confidence=0.75,
            timestamp=datetime.now(),
            price=50000.0,
            explanation="Test explanation",
        )
        assert signal.action == TradeAction.BUY
        assert signal.confidence == 0.75

    def test_portfolio_position(self):
        pos = PortfolioPosition(
            symbol="BTCUSDT",
            quantity=0.1,
            entry_price=50000.0,
            current_price=51000.0,
        )
        assert pos.unrealized_pnl == 100.0
        assert pos.unrealized_pnl_percent == 2.0

    def test_portfolio_calculation(self):
        portfolio = Portfolio(balance=10000.0)
        portfolio.calculate_total_value({"BTCUSDT": 50000.0})
        assert portfolio.total_value == 10000.0

        pos = PortfolioPosition(
            symbol="BTCUSDT",
            quantity=0.1,
            entry_price=50000.0,
            current_price=50000.0,
        )
        portfolio.positions["BTCUSDT"] = pos
        portfolio.calculate_total_value({"BTCUSDT": 50000.0})
        assert portfolio.total_value == 15000.0


class TestTechnicalIndicators:
    """Test technical indicators"""

    def test_rsi_calculation(self):
        from src.tools.indicators import calculate_rsi

        prices = [100 + i * 2 for i in range(20)]
        rsi = calculate_rsi(prices)
        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_macd_calculation(self):
        from src.tools.indicators import calculate_macd

        prices = [100 + i * 0.5 for i in range(50)]
        macd, signal, hist = calculate_macd(prices)
        assert macd is not None
        assert signal is not None
        assert hist is not None

    def test_bollinger_bands(self):
        from src.tools.indicators import calculate_bollinger_bands

        prices = [100 + i * 0.5 for i in range(30)]
        upper, middle, lower = calculate_bollinger_bands(prices)
        assert upper is not None
        assert middle is not None
        assert lower is not None
        assert upper > middle > lower


class TestSentimentAnalysis:
    """Test sentiment analysis"""

    def test_sentiment_keywords_positive(self):
        from src.tools.news_client import _analyze_sentiment

        score, label = _analyze_sentiment("Bitcoin surges to new all-time high!")
        assert score > 0
        assert label in ["bullish", "neutral"]

    def test_sentiment_keywords_negative(self):
        from src.tools.news_client import _analyze_sentiment

        score, label = _analyze_sentiment("Bitcoin crashes as market faces crash")
        assert score < 0
        assert label in ["bearish", "neutral"]


class TestRiskManagement:
    """Test risk management functions"""

    def test_position_sizing(self):
        from src.agents.risk_manager import calculate_position_size

        result = calculate_position_size(0.8, 50000.0)
        assert result["position_value"] > 0
        assert result["quantity"] > 0

    def test_stop_loss_take_profit(self):
        from src.agents.risk_manager import calculate_stop_loss_take_profit

        result = calculate_stop_loss_take_profit(50000.0)
        assert result["stop_loss"] < 50000.0
        assert result["take_profit"] > 50000.0


class TestPaperTrader:
    """Test paper trading"""

    def test_execute_buy(self):
        from src.trading.paper_trader import PaperTrader

        trader = PaperTrader(initial_balance=10000.0)
        trader.set_price("BTCUSDT", 50000.0)

        signal = TradeSignal(
            symbol="BTCUSDT",
            action=TradeAction.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            price=50000.0,
            explanation="Test buy",
        )

        result = trader.execute_signal(signal)
        assert result["status"] == "executed"
        assert "BTCUSDT" in trader.positions

    def test_execute_sell(self):
        from src.trading.paper_trader import PaperTrader

        trader = PaperTrader(initial_balance=10000.0)
        trader.set_price("BTCUSDT", 50000.0)

        buy_signal = TradeSignal(
            symbol="BTCUSDT",
            action=TradeAction.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            price=50000.0,
            explanation="Test buy",
        )
        trader.execute_signal(buy_signal)

        sell_signal = TradeSignal(
            symbol="BTCUSDT",
            action=TradeAction.SELL,
            confidence=0.8,
            timestamp=datetime.now(),
            price=55000.0,
            explanation="Test sell",
        )
        result = trader.execute_signal(sell_signal)
        assert result["status"] == "executed"
        assert "BTCUSDT" not in trader.positions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
