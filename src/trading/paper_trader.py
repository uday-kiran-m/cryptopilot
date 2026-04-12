from datetime import datetime
from typing import Optional

from src.core import get_logger
from src.core.config import settings
from src.core.models import (
    OHLCVData,
    Portfolio,
    PortfolioPosition,
    TradeAction,
    TradeSignal,
)

logger = get_logger("paper_trader")


class PaperTrader:
    """Paper trading simulator that tracks portfolio without real trades"""

    def __init__(self, initial_balance: Optional[float] = None):
        self.initial_balance = initial_balance or settings.initial_balance
        self.balance = self.initial_balance
        self.positions: dict[str, PortfolioPosition] = {}
        self.trade_history: list[dict] = []
        self._prices: dict[str, float] = {}

    def set_price(self, symbol: str, price: float):
        """Update current price for a symbol"""
        self._prices[symbol] = price
        if symbol in self.positions:
            self.positions[symbol].update(price)

    def execute_signal(self, signal: TradeSignal) -> dict:
        """Execute a trade signal (paper trading)"""
        symbol = signal.symbol
        price = signal.price
        action = signal.action

        if action == TradeAction.HOLD:
            logger.info(f"HOLD signal for {symbol} - no action taken")
            return {"status": "skipped", "reason": "HOLD signal"}

        max_position_value = self.initial_balance * settings.max_position_size

        if action == TradeAction.BUY:
            if symbol in self.positions:
                logger.info(f"Already have position in {symbol}, skipping BUY")
                return {"status": "skipped", "reason": "Position exists"}

            quantity = (max_position_value * 0.95) / price

            if self.balance < quantity * price:
                available = self.balance * 0.95
                quantity = available / price

            cost = quantity * price
            if cost > self.balance:
                logger.warning(f"Insufficient balance for {symbol}: {cost} > {self.balance}")
                return {"status": "rejected", "reason": "Insufficient balance"}

            self.balance -= cost
            stop_loss = price * (1 - settings.stop_loss_percent / 100)
            take_profit = price * (1 + settings.take_profit_percent / 100)

            self.positions[symbol] = PortfolioPosition(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                current_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

            trade_record = {
                "timestamp": datetime.now(),
                "symbol": symbol,
                "action": "BUY",
                "quantity": quantity,
                "price": price,
                "cost": cost,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": signal.confidence,
                "explanation": signal.explanation,
            }
            self.trade_history.append(trade_record)

            logger.info(
                f"BUY {quantity:.6f} {symbol} @ {price}, cost: {cost:.2f}, "
                f"stop: {stop_loss:.2f}, target: {take_profit:.2f}"
            )

            return {"status": "executed", "trade": trade_record}

        elif action == TradeAction.SELL:
            if symbol not in self.positions:
                logger.warning(f"No position to sell for {symbol}")
                return {"status": "rejected", "reason": "No position"}

            position = self.positions[symbol]
            proceeds = position.quantity * price
            pnl = proceeds - (position.entry_price * position.quantity)

            trade_record = {
                "timestamp": datetime.now(),
                "symbol": symbol,
                "action": "SELL",
                "quantity": position.quantity,
                "price": price,
                "proceeds": proceeds,
                "pnl": pnl,
                "confidence": signal.confidence,
                "explanation": signal.explanation,
            }
            self.trade_history.append(trade_record)

            self.balance += proceeds
            del self.positions[symbol]

            logger.info(
                f"SELL {position.quantity:.6f} {symbol} @ {price}, "
                f"proceeds: {proceeds:.2f}, P&L: {pnl:.2f}"
            )

            return {"status": "executed", "trade": trade_record}

        return {"status": "skipped", "reason": "Unknown action"}

    def check_stop_loss_take_profit(self, symbol: str) -> Optional[str]:
        """Check if stop loss or take profit is hit"""
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        price = self._prices.get(symbol, position.current_price)

        if position.stop_loss and price <= position.stop_loss:
            return "STOP_LOSS"

        if position.take_profit and price >= position.take_profit:
            return "TAKE_PROFIT"

        return None

    def get_portfolio(self) -> Portfolio:
        """Get current portfolio state"""
        portfolio = Portfolio(balance=self.balance, positions=self.positions)

        for symbol in self.positions:
            if symbol not in self._prices:
                self._prices[symbol] = self.positions[symbol].current_price

        portfolio.calculate_total_value(self._prices)
        return portfolio

    def get_open_positions(self) -> list[PortfolioPosition]:
        """Get list of open positions"""
        return list(self.positions.values())

    def get_trade_history(self) -> list[dict]:
        """Get trade history"""
        return self.trade_history

    def get_performance_summary(self) -> dict:
        """Get performance summary"""
        total_trades = len(self.trade_history)
        winning_trades = [t for t in self.trade_history if t.get("pnl", 0) > 0]
        losing_trades = [t for t in self.trade_history if t.get("pnl", 0) < 0]

        total_pnl = sum(t.get("pnl", 0) for t in self.trade_history)
        portfolio = self.get_portfolio()

        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / total_trades if total_trades > 0 else 0,
            "total_pnl": total_pnl,
            "current_balance": self.balance,
            "total_portfolio_value": portfolio.total_value,
            "total_return_percent": portfolio.total_pnl_percent,
        }


paper_trader = PaperTrader()
