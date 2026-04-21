import sys
import os
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.schema.models import (
    MarketDataPacket,
    SentimentResult,
    AnalystSignal,
    RiskAssessment,
    TradeRecommendation,
    TradeAction,
    AnalysisResult,
    Portfolio,
    PriceSnapshot,
    TrendData,
    RSIData,
    BollingerData,
    EMAData,
    PriceLevels,
    VolumeData,
    VolatilityData,
    StochasticData,
)
from src.agents.sentiment_analyzer import SentimentAnalyzer
from src.agents.live_data_agent import LiveDataAgent
from src.agents.trade_queue import TradeQueue
from src.core.knowledge_base import TradingKnowledgeBase


class TradingOrchestrator:
    """
    Main orchestrator that coordinates all agents:
    - LiveDataAgent: fetches market data
    - SentimentAnalyzer: provides sentiment score
    - AnalystAgent: generates trading signals
    - RiskManagerAgent: validates and sizes trades
    - TradeQueue: executes approved trades
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        symbol: str = "BTCUSDT",
        timeframe: str = "4h",
        lookback: int = 55,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        self.lookback = lookback

        self.sentiment_analyzer: Optional[SentimentAnalyzer] = None
        self.live_data_agent: Optional[LiveDataAgent] = None
        self.analyst_agent = None
        self.risk_manager_agent = None
        self.trade_queue: Optional[TradeQueue] = None

        self._knowledge_base = None
        self._initialized = False
        self._last_analysis: Optional[AnalysisResult] = None

    def initialize(self) -> bool:
        """
        Initialize all agents and components.
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True

        try:
            # Initialize Knowledge Base
            print("Initializing Knowledge Base...")
            kb_path = os.path.join(
                os.path.dirname(__file__), "../../data/strategies/strategies_processed.json"
            )
            db_dir = os.path.join(os.path.dirname(__file__), "../../database/chroma_db")
            self._knowledge_base = TradingKnowledgeBase(
                json_path=kb_path,
                db_dir=db_dir
            )

            # Initialize Analyst Agent
            print("Initializing Analyst Agent...")
            from src.agents.analyst import AnalystAgent
            self.analyst_agent = AnalystAgent(
                knowledge_base=self._knowledge_base,
                timeframe_hours=int(self.timeframe.replace("h", ""))
            )

            # Initialize Risk Manager Agent
            print("Initializing Risk Manager Agent...")
            from src.agents.risk_manager import RiskManagerAgent
            self.risk_manager_agent = RiskManagerAgent(
                total_equity=self.initial_balance,
                timeframe_hours=int(self.timeframe.replace("h", ""))
            )

            # Initialize other agents
            self.sentiment_analyzer = SentimentAnalyzer(use_stub=True, fixed_score=0.5)
            self.live_data_agent = LiveDataAgent(
                symbol=self.symbol,
                timeframe=self.timeframe,
                lookback=self.lookback
            )
            self.trade_queue = TradeQueue()
            self.trade_queue._portfolio.balance = self.initial_balance

            self._initialized = True
            print(f"TradingOrchestrator initialized successfully!")
            return True

        except Exception as e:
            print(f"Error initializing TradingOrchestrator: {e}")
            return False

    def _build_market_data_dict(self, market_data: MarketDataPacket) -> dict:
        """Convert MarketDataPacket to dict format expected by AnalystAgent"""
        return {
            "asset_name": market_data.asset_name,
            "snapshot": {
                "close": market_data.snapshot.close,
                "open": market_data.snapshot.open,
                "high": market_data.snapshot.high,
                "low": market_data.snapshot.low,
            },
            "trends": {
                "market_structure": market_data.trends.market_structure,
                "pct_change_50": market_data.trends.pct_change_50,
                "pct_change_10": market_data.trends.pct_change_10,
            },
            "rsi": {
                "current": market_data.rsi.current,
                "prev": market_data.rsi.prev,
                "avg_50": market_data.rsi.avg_50,
                "trend": market_data.rsi.trend,
            },
            "bands": {
                "upper": market_data.bands.upper,
                "lower": market_data.bands.lower,
                "position_label": market_data.bands.position_label,
            },
            "ema": {
                "value": market_data.ema.value,
                "price_rel": market_data.ema.price_rel,
                "slope": market_data.ema.slope,
            },
            "levels": {
                "high_50": market_data.levels.high_50,
                "low_50": market_data.levels.low_50,
                "high_20": market_data.levels.high_20,
                "low_20": market_data.levels.low_20,
                "high_55": market_data.levels.high_55,
                "low_55": market_data.levels.low_55,
            },
            "volume": {
                "current": market_data.volume.current,
                "avg_50": market_data.volume.avg_50,
                "is_spike": market_data.volume.is_spike,
            },
            "volatility": {
                "atr": market_data.volatility.atr,
            },
            "stochastic": {
                "current": market_data.stochastic.current,
            },
        }

    async def run_analysis_cycle(self) -> AnalysisResult:
        """
        Run a complete analysis cycle.
        
        Steps:
        1. Get market data from LiveDataAgent
        2. Get sentiment from SentimentAnalyzer
        3. Pass to AnalystAgent
        4. Pass to RiskManagerAgent
        5. Add approved trades to queue
        
        Returns:
            AnalysisResult with all details
        """
        if not self._initialized:
            self.initialize()

        try:
            # Step 1: Get market data
            print(f"[Orchestrator] Fetching market data for {self.symbol}...")
            market_data = self.live_data_agent.get_market_data()
            market_data_dict = self._build_market_data_dict(market_data)

            # Step 2: Get sentiment
            print("[Orchestrator] Analyzing sentiment...")
            sentiment_result = self.sentiment_analyzer.analyze(self.symbol)
            sentiment_score = sentiment_result.score

            # Step 3: Get analyst signal
            print("[Orchestrator] Generating analyst signal...")
            try:
                analyst_signal = self.analyst_agent.analyze(
                    market_data=market_data_dict,
                    sentiment_score=sentiment_score
                )
            except Exception as e:
                print(f"[Orchestrator] LLM failed, using fallback: {e}")
                analyst_signal = self.analyst_agent.analyze_fallback(
                    market_data=market_data_dict,
                    sentiment_score=sentiment_score
                )

            # Step 4: Get risk assessment
            print("[Orchestrator] Evaluating risk...")
            current_portfolio = self.trade_queue.portfolio.positions
            risk_assessment = self.risk_manager_agent.evaluate(
                analyst_signal=AnalystSignal(
                    signal=analyst_signal.signal,
                    confidence=analyst_signal.confidence,
                    strategy_used=analyst_signal.strategy_used,
                    reasoning=analyst_signal.reasoning,
                    internal_monologue=analyst_signal.internal_monologue,
                    entry_condition=analyst_signal.entry_condition,
                    exit_condition=analyst_signal.exit_condition,
                    valid_till=analyst_signal.valid_till,
                    asset_name=analyst_signal.asset_name,
                ),
                market_data=market_data_dict,
                sentiment_score=sentiment_score,
                current_portfolio=list(current_portfolio.values()) if current_portfolio else [],
            )

            # Step 5: Create trade recommendation and add to queue
            recommendation: Optional[TradeRecommendation] = None

            if risk_assessment.signal != "HOLD" and risk_assessment.is_approved:
                recommendation = TradeRecommendation(
                    asset_name=self.symbol,
                    signal=TradeAction(risk_assessment.signal),
                    entry_price=market_data.snapshot.close,
                    position_size=risk_assessment.position_size,
                    stop_loss=risk_assessment.stop_loss,
                    take_profit=risk_assessment.target,
                    confidence=analyst_signal.confidence,
                    strategy_used=analyst_signal.strategy_used,
                    reasoning=analyst_signal.reasoning,
                )

                # Add to queue
                self.trade_queue.add_trade(recommendation)
                print(f"[Orchestrator] Trade added to queue: {recommendation.signal} {recommendation.asset_name}")

            result = AnalysisResult(
                timestamp=datetime.now(),
                symbol=self.symbol,
                market_data=market_data,
                sentiment_score=sentiment_score,
                analyst_signal=analyst_signal,
                risk_assessment=RiskAssessment(
                    asset_name=risk_assessment.asset_name,
                    signal=risk_assessment.signal,
                    entry_condition=risk_assessment.entry_condition,
                    exit_condition=risk_assessment.exit_condition,
                    target=risk_assessment.target,
                    stop_loss=risk_assessment.stop_loss,
                    position_size=risk_assessment.position_size,
                    timeframe=risk_assessment.timeframe,
                    audit_summary=risk_assessment.audit_summary,
                    valid_until=risk_assessment.valid_until,
                    risk_score=5,
                    is_approved=risk_assessment.is_approved,
                ),
                recommendation=recommendation,
            )

            self._last_analysis = result
            return result

        except Exception as e:
            print(f"[Orchestrator] Error in analysis cycle: {e}")
            import traceback
            traceback.print_exc()
            
            # Create empty market data with proper defaults
            empty_market_data = MarketDataPacket(
                snapshot=PriceSnapshot(open=0, high=0, low=0, close=0),
                trends=TrendData(pct_change_50=0, pct_change_10=0, market_structure="Unknown"),
                rsi=RSIData(current=50, prev=50, avg_50=50, trend="Neutral"),
                bands=BollingerData(upper=0, lower=0, position_label="Unknown"),
                ema=EMAData(value=0, price_rel="Unknown", slope="Neutral"),
                levels=PriceLevels(high_50=0, low_50=0, high_20=0, low_20=0, high_55=0, low_55=0),
                volume=VolumeData(current=0, avg_50=0, is_spike=False),
                volatility=VolatilityData(atr=0),
                stochastic=StochasticData(current=50),
                asset_name=self.symbol,
            )
            
            return AnalysisResult(
                timestamp=datetime.now(),
                symbol=self.symbol,
                market_data=empty_market_data,
                sentiment_score=0.5,
                analyst_signal=AnalystSignal(
                    signal="HOLD",
                    confidence=0.0,
                    strategy_used="error",
                    reasoning=str(e),
                    internal_monologue="",
                    entry_condition="",
                    exit_condition="",
                    valid_till="",
                    asset_name=self.symbol,
                ),
                risk_assessment=RiskAssessment(
                    asset_name=self.symbol,
                    signal="HOLD",
                    entry_condition="",
                    exit_condition="",
                    target=0.0,
                    stop_loss=0.0,
                    position_size=0.0,
                    timeframe=self.timeframe,
                    audit_summary=str(e),
                    valid_until="",
                    is_approved=False,
                ),
                error=str(e),
            )

    def get_portfolio(self) -> Portfolio:
        """Get current portfolio"""
        return self.trade_queue.portfolio if self.trade_queue else Portfolio(balance=self.initial_balance)

    def get_pending_trades(self) -> list:
        """Get pending trades in queue"""
        return self.trade_queue.get_pending_trades() if self.trade_queue else []

    def get_trade_history(self) -> list:
        """Get executed trade history"""
        return self.trade_queue.get_trade_history() if self.trade_queue else []

    def get_performance(self) -> dict:
        """Get performance summary"""
        return self.trade_queue.get_performance_summary() if self.trade_queue else {}

    def get_last_analysis(self) -> Optional[AnalysisResult]:
        """Get last analysis result"""
        return self._last_analysis


# Singleton instance
_orchestrator: Optional[TradingOrchestrator] = None


def get_orchestrator(
    initial_balance: float = 10000.0,
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
) -> TradingOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TradingOrchestrator(
            initial_balance=initial_balance,
            symbol=symbol,
            timeframe=timeframe,
        )
    return _orchestrator
