import queue
import threading
from datetime import datetime
from typing import Optional, List
from ..schema.models import TradeRecommendation, TradeAction, Portfolio


class TradeQueue:
    """
    Thread-safe queue for managing trade recommendations.
    Handles adding, retrieving, and executing trades.
    """

    def __init__(self, max_size: int = 10):
        self._queue = queue.Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._executed_trades: List[TradeRecommendation] = []
        self._portfolio = Portfolio(balance=10000.0)

    @property
    def portfolio(self) -> Portfolio:
        """Get current portfolio state"""
        return self._portfolio

    def add_trade(self, recommendation: TradeRecommendation) -> bool:
        """
        Add a trade recommendation to the queue.
        
        Args:
            recommendation: TradeRecommendation to add
            
        Returns:
            True if added successfully, False if queue is full
        """
        try:
            self._queue.put_nowait(recommendation)
            return True
        except queue.Full:
            return False

    def get_pending_trades(self) -> List[TradeRecommendation]:
        """Get all pending trades without removing them"""
        with self._lock:
            return list(self._queue.queue)

    def execute_trade(self, recommendation: TradeRecommendation) -> dict:
        """
        Execute a trade (paper trading).
        
        Args:
            recommendation: TradeRecommendation to execute
            
        Returns:
            dict with execution status and details
        """
        if recommendation.signal == TradeAction.HOLD:
            recommendation.status = "cancelled"
            return {"status": "cancelled", "reason": "HOLD signal"}

        if recommendation.status != "pending":
            return {"status": "skipped", "reason": f"Already {recommendation.status}"}

        current_price = recommendation.entry_price
        trade_value = recommendation.position_size

        if recommendation.signal == TradeAction.BUY:
            if trade_value > self._portfolio.balance:
                recommendation.status = "rejected"
                return {"status": "rejected", "reason": "Insufficient balance"}

            quantity = trade_value / current_price
            cost = quantity * current_price

            if cost > self._portfolio.balance:
                recommendation.status = "rejected"
                return {"status": "rejected", "reason": "Insufficient balance"}

            self._portfolio.balance -= cost

            from src.schema.models import Position
            self._portfolio.positions[recommendation.asset_name] = Position(
                symbol=recommendation.asset_name,
                quantity=quantity,
                entry_price=current_price,
                current_price=current_price,
                stop_loss=recommendation.stop_loss,
                take_profit=recommendation.take_profit
            )

            recommendation.status = "executed"
            self._executed_trades.append(recommendation)

            return {
                "status": "executed",
                "trade": {
                    "id": recommendation.id,
                    "action": "BUY",
                    "symbol": recommendation.asset_name,
                    "quantity": quantity,
                    "price": current_price,
                    "cost": cost,
                    "stop_loss": recommendation.stop_loss,
                    "take_profit": recommendation.take_profit,
                }
            }

        elif recommendation.signal == TradeAction.SELL:
            if recommendation.asset_name not in self._portfolio.positions:
                recommendation.status = "rejected"
                return {"status": "rejected", "reason": "No position to sell"}

            position = self._portfolio.positions[recommendation.asset_name]
            proceeds = position.quantity * current_price
            pnl = proceeds - (position.entry_price * position.quantity)

            self._portfolio.balance += proceeds
            del self._portfolio.positions[recommendation.asset_name]

            recommendation.status = "executed"
            self._executed_trades.append(recommendation)

            return {
                "status": "executed",
                "trade": {
                    "id": recommendation.id,
                    "action": "SELL",
                    "symbol": recommendation.asset_name,
                    "quantity": position.quantity,
                    "price": current_price,
                    "proceeds": proceeds,
                    "pnl": pnl,
                }
            }

        recommendation.status = "cancelled"
        return {"status": "cancelled", "reason": "Unknown signal"}

    def process_next_trade(self) -> Optional[dict]:
        """
        Process the next trade in the queue.
        
        Returns:
            dict with execution result, or None if queue is empty
        """
        try:
            recommendation = self._queue.get_nowait()
            return self.execute_trade(recommendation)
        except queue.Empty:
            return None

    def cancel_all_pending(self) -> int:
        """Cancel all pending trades"""
        cancelled = 0
        with self._lock:
            while not self._queue.empty():
                try:
                    recommendation = self._queue.get_nowait()
                    recommendation.status = "cancelled"
                    cancelled += 1
                except queue.Empty:
                    break
        return cancelled

    def get_executed_trades(self) -> List[TradeRecommendation]:
        """Get all executed trades"""
        return self._executed_trades.copy()

    def get_trade_history(self) -> List[dict]:
        """Get full trade history as dicts"""
        history = []
        for trade in self._executed_trades:
            history.append({
                "id": trade.id,
                "timestamp": trade.timestamp,
                "symbol": trade.asset_name,
                "signal": trade.signal,
                "entry_price": trade.entry_price,
                "position_size": trade.position_size,
                "status": trade.status,
            })
        return history

    def update_portfolio_prices(self, prices: dict[str, float]):
        """Update portfolio with current prices"""
        self._portfolio.calculate_total_value(prices)

    def get_performance_summary(self) -> dict:
        """Get performance summary"""
        total_trades = len(self._executed_trades)
        winning_trades = [
            t for t in self._executed_trades 
            if t.signal == TradeAction.SELL and t.take_profit > t.entry_price
        ]

        total_pnl = 0.0
        for trade in self._executed_trades:
            if trade.signal == TradeAction.SELL:
                position_value = trade.position_size
                pnl = (trade.take_profit - trade.entry_price) / trade.entry_price * position_value
                total_pnl += pnl

        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": total_trades - len(winning_trades),
            "win_rate": len(winning_trades) / total_trades if total_trades > 0 else 0,
            "total_pnl": total_pnl,
            "current_balance": self._portfolio.balance,
            "total_portfolio_value": self._portfolio.total_value,
            "total_return_percent": self._portfolio.total_pnl_percent,
        }


def create_trade_queue(initial_balance: float = 10000.0) -> TradeQueue:
    """Factory function to create a trade queue with initial balance"""
    tq = TradeQueue()
    tq._portfolio.balance = initial_balance
    return tq
