import asyncio
from datetime import datetime
from typing import Optional

from crewai import Agent, Crew, Process, Task

from src.agents.data_agent import fetch_market_data, analyze_data_quality
from src.agents.risk_manager import (
    check_risk_limits,
    create_risk_manager_agent,
    calculate_portfolio_risk,
)
from src.agents.sentiment_agent import analyze_symbol_sentiment
from src.agents.signal_generator import signal_generator
from src.agents.technical_agent import analyze_technical_indicators
from src.core import get_logger
from src.core.config import settings
from src.core.models import TradeSignal
from src.trading.paper_trader import paper_trader

logger = get_logger("orchestrator")


class CryptoPilotOrchestrator:
    """Main orchestrator for the multi-agent crypto trading system"""

    def __init__(self):
        self.symbols = settings.symbols
        self.llm = None

    async def initialize(self):
        """Initialize the orchestrator and LLM"""
        try:
            from langchain_ollama import ChatOllama

            self.llm = ChatOllama(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
            )
            logger.info(f"Initialized Ollama LLM: {settings.ollama_model}")
        except Exception as e:
            logger.warning(f"Could not initialize Ollama LLM: {e}")
            logger.warning("Will use fallback explanations without LLM")

    async def analyze_symbol(self, symbol: str) -> TradeSignal:
        """Analyze a single symbol and generate a trading signal"""
        logger.info(f"Analyzing {symbol}...")

        data = await fetch_market_data(symbol, interval="1h", limit=100)
        quality = analyze_data_quality(data)

        if not quality["is_valid"]:
            logger.warning(f"Data quality issues for {symbol}: {quality['issues']}")

        indicators = data.get("indicators")
        price = data.get("current_price") or 0

        sentiment = await analyze_symbol_sentiment(symbol)

        technical_analysis = {}
        if indicators:
            technical_analysis = analyze_technical_indicators(indicators, price)

        portfolio = paper_trader.get_portfolio()
        positions = paper_trader.get_open_positions()

        risk_checks = check_risk_limits(
            symbol=symbol,
            proposed_action=technical_analysis.get("signal", "HOLD"),
            current_positions=positions,
            total_value=portfolio.total_value,
        )

        proposed_action = technical_analysis.get("signal", "HOLD")

        signal = await signal_generator.generate_signal(
            symbol=symbol,
            price=price,
            technical=indicators,
            sentiment=sentiment,
            technical_analysis=technical_analysis,
            risk_checks=risk_checks,
        )

        logger.info(
            f"{symbol}: {signal.action.value} @ {price:.2f} "
            f"(confidence: {signal.confidence:.1%})"
        )

        return signal

    async def run_full_analysis(self) -> dict[str, TradeSignal]:
        """Run analysis on all symbols"""
        logger.info("Starting full analysis for all symbols...")

        results = {}
        for symbol in self.symbols:
            try:
                signal = await self.analyze_symbol(symbol)
                results[symbol] = signal
                paper_trader.set_price(symbol, signal.price)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                results[symbol] = None

        return results

    async def execute_signals(self, signals: dict[str, TradeSignal]) -> dict:
        """Execute trading signals based on paper trading"""
        executions = {}

        for symbol, signal in signals.items():
            if signal is None:
                continue

            paper_trader.set_price(symbol, signal.price)

            stop_tp_check = paper_trader.check_stop_loss_take_profit(symbol)
            if stop_tp_check:
                logger.info(
                    f"{symbol}: {stop_tp_check} triggered, closing position"
                )
                result = paper_trader.execute_signal(signal)
                executions[symbol] = result
                continue

            result = paper_trader.execute_signal(signal)
            executions[symbol] = result

        return executions

    async def run_trading_cycle(self) -> dict:
        """Run complete trading cycle: analyze + execute"""
        signals = await self.run_full_analysis()
        executions = await self.execute_signals(signals)

        portfolio = paper_trader.get_portfolio()
        performance = paper_trader.get_performance_summary()

        return {
            "timestamp": datetime.now(),
            "signals": signals,
            "executions": executions,
            "portfolio": portfolio,
            "performance": performance,
        }


orchestrator = CryptoPilotOrchestrator()
