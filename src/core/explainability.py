import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core import get_logger
from src.core.config import settings

logger = get_logger("explainability")

_explainability_logger = None


def get_explainability_logger():
    """Get or create the explainability logger singleton"""
    global _explainability_logger
    if _explainability_logger is None:
        _explainability_logger = ExplainabilityLogger()
    return _explainability_logger


class ExplainabilityLogger:
    """Comprehensive logging for explainability and audit trails"""

    def __init__(self):
        self.log_dir = settings.logs_dir
        self.log_dir.mkdir(exist_ok=True)
        self.decisions_file = self.log_dir / "decisions.jsonl"
        self.agents_file = self.log_dir / "agent_decisions.jsonl"
        self._buffer = []

    def log_agent_decision(
        self,
        agent_name: str,
        task: str,
        inputs: dict,
        outputs: dict,
        reasoning: str,
        confidence: Optional[float] = None,
        metadata: Optional[dict] = None,
    ):
        """Log an agent's decision with full context"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "task": task,
            "inputs": self._sanitize(inputs),
            "outputs": self._sanitize(outputs),
            "reasoning": reasoning,
            "confidence": confidence,
            "metadata": metadata or {},
        }

        self._buffer.append(entry)

        try:
            with open(self.agents_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write agent decision: {e}")

        logger.debug(
            f"[{agent_name}] {task}: {reasoning[:100]}..."
        )

    def log_signal_decision(
        self,
        symbol: str,
        action: str,
        confidence: float,
        factors: dict,
        explanation: str,
        technical_snapshot: Optional[dict] = None,
        sentiment_snapshot: Optional[dict] = None,
    ):
        """Log a final trading signal decision"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "decision_type": "TRADING_SIGNAL",
            "symbol": symbol,
            "action": action,
            "confidence": confidence,
            "factors": factors,
            "explanation": explanation,
            "technical_snapshot": technical_snapshot,
            "sentiment_snapshot": sentiment_snapshot,
        }

        try:
            with open(self.decisions_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write signal decision: {e}")

        logger.info(
            f"[SIGNAL] {symbol}: {action} ({confidence:.1%}) - {explanation[:80]}"
        )

    def _sanitize(self, data: dict) -> dict:
        """Remove non-serializable objects from dict"""
        sanitized = {}
        for key, value in data.items():
            try:
                if hasattr(value, "__dict__"):
                    sanitized[key] = str(value)
                elif isinstance(value, (datetime, Path)):
                    sanitized[key] = str(value)
                elif isinstance(value, dict):
                    sanitized[key] = self._sanitize(value)
                elif isinstance(value, list):
                    sanitized[key] = [
                        self._sanitize(v) if isinstance(v, dict) else v
                        for v in value[:50]
                    ]
                else:
                    sanitized[key] = value
            except Exception:
                sanitized[key] = str(value)
        return sanitized

    def get_decision_history(self, limit: int = 100, decision_type: Optional[str] = None) -> list[dict]:
        """Retrieve decision history from log files"""
        decisions = []
        file_path = (
            self.decisions_file if decision_type == "TRADING_SIGNAL"
            else self.agents_file
        )

        if not file_path.exists():
            return decisions

        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            for line in lines[-limit:]:
                try:
                    decision = json.loads(line.strip())
                    decisions.append(decision)
                except json.JSONDecodeError:
                    continue

            decisions.reverse()
        except Exception as e:
            logger.error(f"Failed to read decision history: {e}")

        return decisions

    def generate_factor_attribution(self, symbol: str, limit: int = 20) -> dict:
        """Generate factor attribution report for a symbol"""
        history = self.get_decision_history(
            limit=limit,
            decision_type="TRADING_SIGNAL"
        )

        symbol_history = [d for d in history if d.get("symbol") == symbol]

        if not symbol_history:
            return {
                "symbol": symbol,
                "sample_size": 0,
                "average_factors": {"technical": 0.33, "sentiment": 0.33, "risk": 0.34},
            }

        factor_totals = {"technical": 0, "sentiment": 0, "risk": 0}
        for decision in symbol_history:
            factors = decision.get("factors", {})
            for key, value in factors.items():
                if key in factor_totals:
                    factor_totals[key] += value

        count = len(symbol_history)
        return {
            "symbol": symbol,
            "sample_size": count,
            "average_factors": {
                key: val / count for key, val in factor_totals.items()
            },
            "total_decisions": count,
            "actions": {
                "BUY": sum(1 for d in symbol_history if d.get("action") == "BUY"),
                "SELL": sum(1 for d in symbol_history if d.get("action") == "SELL"),
                "HOLD": sum(1 for d in symbol_history if d.get("action") == "HOLD"),
            },
        }

    def export_audit_report(self, output_path: Optional[Path] = None) -> str:
        """Export complete audit report as JSON"""
        if output_path is None:
            output_path = self.log_dir / f"audit_report_{datetime.now():%Y%m%d_%H%M%S}.json"

        report = {
            "generated_at": datetime.now().isoformat(),
            "symbols_analyzed": list(settings.symbols),
            "agent_decisions": self.get_decision_history(limit=1000, decision_type="AGENT"),
            "signal_decisions": self.get_decision_history(limit=1000, decision_type="TRADING_SIGNAL"),
        }

        for symbol in settings.symbols:
            report[f"{symbol}_factor_attribution"] = self.generate_factor_attribution(symbol)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Exported audit report to {output_path}")
        return str(output_path)
