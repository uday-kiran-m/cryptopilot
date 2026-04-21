import asyncio
import signal
import sys
import os
from datetime import datetime
from typing import Optional, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.orchestrator import TradingOrchestrator, get_orchestrator


class TradingScheduler:
    """
    Scheduler that runs the trading cycle at configurable intervals.
    Default interval is 4 hours.
    """

    def __init__(
        self,
        orchestrator: Optional[TradingOrchestrator] = None,
        interval_hours: float = 4.0,
        initial_balance: float = 10000.0,
        symbol: str = "BTCUSDT",
        timeframe: str = "4h",
    ):
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600

        self.orchestrator = orchestrator or get_orchestrator(
            initial_balance=initial_balance,
            symbol=symbol,
            timeframe=timeframe,
        )

        self._running = False
        self._shutdown_requested = False
        self._cycle_count = 0

        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        print("\nShutdown signal received...")
        self._shutdown_requested = True

    async def run_cycle(self) -> dict:
        """Run a single trading cycle"""
        self._cycle_count += 1
        print(f"\n{'#' * 60}")
        print(f"Trading Cycle #{self._cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#' * 60}")

        try:
            result = await self.orchestrator.run_analysis_cycle()

            print(f"\nAnalysis Result:")
            print(f"  Signal: {result.analyst_signal.signal}")
            print(f"  Confidence: {result.analyst_signal.confidence:.1%}")
            print(f"  Strategy: {result.analyst_signal.strategy_used}")
            print(f"  Reasoning: {result.analyst_signal.reasoning[:100]}...")

            if result.recommendation:
                print(f"  Trade: {result.recommendation.signal} "
                      f"{result.recommendation.asset_name} @ ${result.recommendation.entry_price:,.2f}")
                print(f"  Position Size: ${result.recommendation.position_size:,.2f}")

            print(f"\nRisk Assessment:")
            print(f"  Signal: {result.risk_assessment.signal}")
            print(f"  Approved: {result.risk_assessment.is_approved}")
            print(f"  Position Size: ${result.risk_assessment.position_size:,.2f}")

            return {
                "cycle": self._cycle_count,
                "status": "success",
                "signal": result.analyst_signal.signal,
                "confidence": result.analyst_signal.confidence,
                "error": result.error,
            }

        except Exception as e:
            print(f"Error in trading cycle: {e}")
            import traceback
            traceback.print_exc()
            return {
                "cycle": self._cycle_count,
                "status": "error",
                "error": str(e),
            }

    async def start(self, on_cycle_complete: Optional[Callable] = None):
        """
        Start the scheduler loop.
        
        Args:
            on_cycle_complete: Optional callback function called after each cycle
        """
        print(f"Starting TradingScheduler...")
        print(f"  Interval: {self.interval_hours} hours ({self.interval_seconds} seconds)")
        print(f"  Symbol: {self.orchestrator.symbol}")
        print(f"  Initial Balance: ${self.orchestrator.initial_balance:,.2f}")
        print(f"\nPress Ctrl+C to stop\n")

        self._running = True

        try:
            while self._running and not self._shutdown_requested:
                # Initialize orchestrator on first cycle
                if not self.orchestrator._initialized:
                    self.orchestrator.initialize()

                # Run cycle
                cycle_result = await self.run_cycle()

                # Call callback if provided
                if on_cycle_complete:
                    on_cycle_complete(cycle_result)

                # Sleep until next cycle (or exit if shutdown requested)
                if not self._shutdown_requested:
                    print(f"\nSleeping for {self.interval_hours} hours...")
                    await asyncio.sleep(self.interval_seconds)

        except KeyboardInterrupt:
            print("\nScheduler interrupted by user")
        finally:
            self._running = False
            print("Scheduler stopped.")

    def stop(self):
        """Stop the scheduler"""
        self._running = False


def run_scheduler(
    interval_hours: float = 4.0,
    initial_balance: float = 10000.0,
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
):
    """Convenience function to run the scheduler"""
    orchestrator = get_orchestrator(
        initial_balance=initial_balance,
        symbol=symbol,
        timeframe=timeframe,
    )

    scheduler = TradingScheduler(
        orchestrator=orchestrator,
        interval_hours=interval_hours,
    )

    asyncio.run(scheduler.start())