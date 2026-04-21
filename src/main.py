#!/usr/bin/env python3
"""
CryptoPilot - Explainable Multi-Agentic AI Crypto Trader

Usage:
    python -m src.main                    # Run analysis once
    python -m src.main --dashboard        # Launch Streamlit dashboard
    python -m src.main --continuous       # Run continuous analysis
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.orchestrator import orchestrator
from src.core import get_logger
from src.core.config import settings

logger = get_logger("main")


async def run_analysis():
    """Run a single analysis cycle"""
    logger.info("Starting CryptoPilot analysis...")

    try:
        await orchestrator.initialize()
        results = await orchestrator.run_trading_cycle()

        print("\n" + "=" * 60)
        print("CRYPTOPILOT ANALYSIS RESULTS")
        print("=" * 60)
        print(f"Timestamp: {results['timestamp']}")
        print("-" * 60)

        for symbol, signal in results["signals"].items():
            if signal:
                print(f"\n{symbol}:")
                print(f"  Action: {signal.action.value}")
                print(f"  Price: ${signal.price:,.2f}")
                print(f"  Confidence: {signal.confidence:.1%}")
                print(f"  Explanation: {signal.explanation}")

                if signal.technical_indicators:
                    ti = signal.technical_indicators
                    print(f"  Technical:")
                    if ti.rsi:
                        print(f"    RSI: {ti.rsi:.2f}")
                    if ti.macd:
                        print(f"    MACD: {ti.macd:.2f}")

                if signal.sentiment:
                    print(f"  Sentiment: {signal.sentiment.overall_score:.2f} "
                          f"(bullish: {signal.sentiment.bullish_count}, "
                          f"bearish: {signal.sentiment.bearish_count})")

        print("\n" + "-" * 60)
        portfolio = results["portfolio"]
        perf = results["performance"]
        print(f"Portfolio Value: ${portfolio.total_value:,.2f}")
        print(f"Total P&L: ${perf['total_pnl']:,.2f} ({perf['total_return_percent']:.2f}%)")
        print(f"Win Rate: {perf['win_rate']:.1%}")
        print("=" * 60)

        return results

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\nError: {e}")
        return None


async def run_continuous(seconds: int = None):
    """Run continuous analysis at specified intervals"""
    interval = seconds or settings.update_interval
    logger.info(f"Starting continuous analysis every {interval} seconds...")

    print(f"\nCryptoPilot Continuous Mode")
    print(f"Update interval: {interval} seconds")
    print(f"Press Ctrl+C to stop\n")

    cycle_count = 0
    try:
        while True:
            cycle_count += 1
            print(f"\n{'#' * 60}")
            print(f"Analysis Cycle #{cycle_count} - {datetime.now():%Y-%m-%d %H:%M:%S}")
            print("#" * 60)

            await run_analysis()

            logger.info(f"Sleeping for {interval} seconds...")
            await asyncio.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nShutting down CryptoPilot...")
        logger.info("CryptoPilot stopped by user")


def run_dashboard():
    """Launch the Streamlit dashboard"""
    import subprocess

    logger.info("Launching Streamlit dashboard...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(__file__).replace("main.py", "dashboard/app.py"),
        "--browser.gatherUsageStats", "false",
        "--server.headless", "true",
    ])


def main():
    parser = argparse.ArgumentParser(
        description="CryptoPilot - Explainable Multi-Agentic AI Crypto Trader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                    Run single analysis
  python -m src.main --dashboard        Launch dashboard
  python -m src.main --continuous       Run continuous analysis
  python -m src.main --interval 300     Continuous with 5 min interval
        """
    )

    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch Streamlit dashboard"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous analysis"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Update interval in seconds (for continuous mode)"
    )

    args = parser.parse_args()

    if args.dashboard:
        run_dashboard()
    elif args.continuous:
        asyncio.run(run_continuous(args.interval))
    else:
        asyncio.run(run_analysis())


if __name__ == "__main__":
    main()
