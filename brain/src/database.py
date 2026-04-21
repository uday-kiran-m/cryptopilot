import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


class TradeDatabase:
    """
    SQLite database for storing trade history and analysis results.
    Used for dashboard history display.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__), "../../../data/trading_history.db"
            )

        self.db_path = db_path

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Analysis results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence REAL NOT NULL,
                strategy_used TEXT,
                reasoning TEXT,
                sentiment_score REAL,
                risk_approved INTEGER,
                position_size REAL,
                stop_loss REAL,
                take_profit REAL,
                market_data_json TEXT,
                raw_signal_json TEXT,
                error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trade_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                status TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL,
                position_size REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                pnl REAL,
                confidence REAL,
                strategy_used TEXT,
                reasoning TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Portfolio history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                balance REAL NOT NULL,
                total_value REAL NOT NULL,
                total_pnl REAL NOT NULL,
                positions_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def save_analysis(self, analysis_result: Dict[str, Any]) -> int:
        """Save an analysis result to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        market_data_json = None
        if analysis_result.get("market_data"):
            market_data_json = json.dumps(
                analysis_result["market_data"],
                default=str
            )

        raw_signal_json = None
        if analysis_result.get("analyst_signal"):
            raw_signal_json = json.dumps(
                analysis_result["analyst_signal"],
                default=str
            )

        cursor.execute("""
            INSERT INTO analysis_results (
                timestamp, symbol, signal, confidence, strategy_used, reasoning,
                sentiment_score, risk_approved, position_size, stop_loss, take_profit,
                market_data_json, raw_signal_json, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis_result.get("timestamp", datetime.now()).isoformat(),
            analysis_result.get("symbol", "BTCUSDT"),
            analysis_result.get("signal", "HOLD"),
            analysis_result.get("confidence", 0.0),
            analysis_result.get("strategy_used", ""),
            analysis_result.get("reasoning", ""),
            analysis_result.get("sentiment_score", 0.5),
            1 if analysis_result.get("risk_approved", False) else 0,
            analysis_result.get("position_size", 0.0),
            analysis_result.get("stop_loss", 0.0),
            analysis_result.get("take_profit", 0.0),
            market_data_json,
            raw_signal_json,
            analysis_result.get("error"),
        ))

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return row_id

    def save_trade(self, trade: Dict[str, Any]) -> int:
        """Save a trade to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trades (
                timestamp, trade_id, symbol, signal, status,
                entry_price, exit_price, quantity, position_size,
                stop_loss, take_profit, pnl, confidence, strategy_used, reasoning
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.get("timestamp", datetime.now()).isoformat(),
            trade.get("id", ""),
            trade.get("symbol", "BTCUSDT"),
            trade.get("signal", "HOLD"),
            trade.get("status", "pending"),
            trade.get("entry_price", 0.0),
            trade.get("exit_price"),
            trade.get("quantity"),
            trade.get("position_size", 0.0),
            trade.get("stop_loss"),
            trade.get("take_profit"),
            trade.get("pnl", 0.0),
            trade.get("confidence", 0.0),
            trade.get("strategy_used", ""),
            trade.get("reasoning", ""),
        ))

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return row_id

    def save_portfolio_snapshot(self, portfolio: Dict[str, Any]) -> int:
        """Save a portfolio snapshot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        positions_json = None
        if portfolio.get("positions"):
            positions_json = json.dumps(portfolio["positions"])

        cursor.execute("""
            INSERT INTO portfolio_history (
                timestamp, balance, total_value, total_pnl, positions_json
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            portfolio.get("balance", 0.0),
            portfolio.get("total_value", 0.0),
            portfolio.get("total_pnl", 0.0),
            positions_json,
        ))

        row_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return row_id

    def get_analysis_history(self, limit: int = 50) -> List[Dict]:
        """Get analysis history"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM analysis_results
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM trades
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_portfolio_history(self, limit: int = 50) -> List[Dict]:
        """Get portfolio history"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM portfolio_history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_latest_analysis(self) -> Optional[Dict]:
        """Get the most recent analysis"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM analysis_results
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None


# Singleton instance
_trade_db: Optional[TradeDatabase] = None


def get_trade_database(db_path: Optional[str] = None) -> TradeDatabase:
    """Get or create the trade database singleton"""
    global _trade_db
    if _trade_db is None:
        _trade_db = TradeDatabase(db_path)
    return _trade_db
