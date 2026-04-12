from datetime import datetime
from typing import Optional

from crewai import Agent
from crewai.tools import BaseTool

from src.core import get_logger
from src.core.config import settings
from src.core.models import Portfolio, PortfolioPosition

logger = get_logger("risk_manager")


class PortfolioRiskTool(BaseTool):
    name: str = "portfolio_risk_calculator"
    description: str = "Calculates portfolio risk metrics and position sizing"

    async def _arun(self, current_positions: list[dict], total_value: float):
        try:
            positions = [PortfolioPosition(**p) if isinstance(p, dict) else p for p in current_positions]
            risk = calculate_portfolio_risk(positions, total_value)
            return risk
        except Exception as e:
            logger.error(f"Error in PortfolioRiskTool: {e}")
            return {}


class PositionSizingTool(BaseTool):
    name: str = "position_sizing_calculator"
    description: str = "Calculates optimal position size based on risk parameters"

    async def _arun(self, signal_confidence: float, price: float, volatility: float = None):
        try:
            size = calculate_position_size(signal_confidence, price, volatility)
            return size
        except Exception as e:
            logger.error(f"Error in PositionSizingTool: {e}")
            return {}


def create_risk_manager_agent() -> Agent:
    """Create the risk management agent"""
    return Agent(
        role="Risk Manager",
        goal="Manage portfolio risk, position sizing, and exposure limits to protect capital",
        backstory="""You are an experienced risk manager with expertise in portfolio management,
        position sizing, and risk control. You ensure that trading decisions align with
        proper risk management principles, including stop losses, position limits,
        and portfolio diversification. Your primary goal is to protect capital while
        maximizing risk-adjusted returns.""",
        tools=[PortfolioRiskTool(), PositionSizingTool()],
        verbose=True,
        allow_delegation=False,
    )


def calculate_portfolio_risk(
    positions: list[PortfolioPosition], total_value: float
) -> dict:
    """Calculate portfolio risk metrics"""
    if not positions:
        return {
            "total_exposure": 0.0,
            "max_position_exposure": 0.0,
            "diversification_score": 1.0,
            "risk_level": "LOW",
        }

    positions_value = sum(p.quantity * p.current_price for p in positions)
    total_exposure = positions_value / total_value if total_value > 0 else 0

    max_exposure = 0.0
    for pos in positions:
        exposure = (pos.quantity * pos.current_price) / total_value if total_value > 0 else 0
        max_exposure = max(max_exposure, exposure)

    num_positions = len(positions)
    diversification_score = min(1.0, num_positions / 5)

    if total_exposure > 0.8:
        risk_level = "CRITICAL"
    elif total_exposure > 0.6:
        risk_level = "HIGH"
    elif total_exposure > 0.4:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "total_exposure": total_exposure,
        "positions_value": positions_value,
        "max_position_exposure": max_exposure,
        "diversification_score": diversification_score,
        "num_positions": num_positions,
        "risk_level": risk_level,
        "timestamp": datetime.now(),
    }


def calculate_position_size(
    signal_confidence: float, price: float, volatility: float = None
) -> dict:
    """Calculate position size based on Kelly Criterion and risk parameters"""
    base_size = settings.initial_balance * settings.max_position_size
    confidence_multiplier = 0.5 + (signal_confidence * 0.5)

    position_value = base_size * confidence_multiplier

    if volatility and volatility > 0:
        risk_adjusted = position_value / (volatility * 2)
        position_value = min(position_value, risk_adjusted)

    quantity = position_value / price if price > 0 else 0

    return {
        "position_value": position_value,
        "quantity": quantity,
        "confidence_multiplier": confidence_multiplier,
        "max_allowed_value": base_size,
        "timestamp": datetime.now(),
    }


def check_risk_limits(
    symbol: str,
    proposed_action: str,
    current_positions: list[PortfolioPosition],
    total_value: float,
) -> dict:
    """Check if proposed action violates risk limits"""
    checks = {
        "approved": True,
        "reasons": [],
        "warnings": [],
    }

    risk = calculate_portfolio_risk(current_positions, total_value)

    if proposed_action == "BUY":
        new_exposure = risk["total_exposure"] + settings.max_position_size
        if new_exposure > 0.8:
            checks["approved"] = False
            checks["reasons"].append(
                f"Would exceed max exposure limit (current: {risk['total_exposure']:.1%})"
            )

        if risk["num_positions"] >= 5:
            checks["approved"] = False
            checks["reasons"].append("Maximum number of positions (5) reached")

        for pos in current_positions:
            if pos.symbol == symbol:
                checks["approved"] = False
                checks["reasons"].append(f"Position already exists for {symbol}")

    if proposed_action == "SELL":
        has_position = any(pos.symbol == symbol for pos in current_positions)
        if not has_position:
            checks["approved"] = False
            checks["reasons"].append(f"No position to sell for {symbol}")

    if risk["risk_level"] == "CRITICAL":
        checks["warnings"].append("Portfolio risk is at CRITICAL level")

    return checks


def calculate_stop_loss_take_profit(
    entry_price: float, atr: float = None
) -> dict:
    """Calculate stop loss and take profit levels"""
    stop_loss_percent = settings.stop_loss_percent
    take_profit_percent = settings.take_profit_percent

    if atr:
        atr_multiplier = 2
        stop_distance = atr * atr_multiplier
        stop_loss = entry_price - stop_distance
        take_profit = entry_price + (stop_distance * 2)
    else:
        stop_loss = entry_price * (1 - stop_loss_percent / 100)
        take_profit = entry_price * (1 + take_profit_percent / 100)

    return {
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "stop_loss_percent": stop_loss_percent,
        "take_profit_percent": take_profit_percent,
        "risk_reward_ratio": (take_profit - entry_price) / (entry_price - stop_loss)
        if entry_price > stop_loss
        else 0,
    }
