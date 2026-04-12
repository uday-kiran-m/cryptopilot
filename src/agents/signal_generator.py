import json
from datetime import datetime
from typing import Optional

import httpx

from src.core import get_logger
from src.core.config import settings
from src.core.models import (
    SentimentAnalysis,
    TechnicalIndicators,
    TradeAction,
    TradeSignal,
)

logger = get_logger("signal_generator")


class OllamaLLM:
    """Ollama LLM wrapper for generating explanations"""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def generate(self, prompt: str, system: str = None) -> str:
        """Generate text using Ollama"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                }
                if system:
                    payload["system"] = system

                response = await client.post(
                    f"{self.base_url}/api/generate", json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            return f"Error generating explanation: {e}"

    async def generate_explanation(
        self,
        symbol: str,
        action: TradeAction,
        confidence: float,
        technical: dict,
        sentiment: dict,
    ) -> str:
        """Generate human-readable explanation for the trading signal"""

        system_prompt = """You are a crypto trading assistant that explains trading signals in clear, 
        concise language. You provide reasons for recommendations and mention key factors.
        Keep explanations under 3 sentences. Be specific about price levels and indicators."""

        prompt = f"""Generate a trading signal explanation for {symbol}:

        Action: {action.value}
        Confidence: {confidence:.1%}
        Technical Indicators:
        - RSI: {technical.get('rsi', 'N/A')}
        - MACD: {technical.get('macd', 'N/A')} (Signal: {technical.get('macd_signal', 'N/A')})
        - Bollinger Upper: {technical.get('bollinger_upper', 'N/A')}
        - Bollinger Middle: {technical.get('bollinger_middle', 'N/A')}
        - Bollinger Lower: {technical.get('bollinger_lower', 'N/A')}
        
        Sentiment:
        - Score: {sentiment.get('overall_score', 0):.2f}
        - Bullish articles: {sentiment.get('bullish_count', 0)}
        - Bearish articles: {sentiment.get('bearish_count', 0)}

        Provide a brief explanation of why this signal was generated."""

        return await self.generate(prompt, system_prompt)


class ExplainabilityLogger:
    """Log decisions for audit trail and explainability"""

    def __init__(self):
        self.decisions: list[dict] = []
        self.log_file = settings.logs_dir / "decisions.jsonl"

    def log_decision(
        self,
        agent_name: str,
        decision_type: str,
        inputs: dict,
        outputs: dict,
        reasoning: str,
        confidence: float = None,
    ):
        """Log a decision for audit trail"""
        decision = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "decision_type": decision_type,
            "inputs": inputs,
            "outputs": outputs,
            "reasoning": reasoning,
            "confidence": confidence,
        }
        self.decisions.append(decision)

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(decision) + "\n")
        except Exception as e:
            logger.error(f"Error writing to decision log: {e}")

    def get_decision_history(self, limit: int = 100) -> list[dict]:
        """Get recent decision history"""
        return self.decisions[-limit:]

    def get_factor_weights(self, symbol: str, limit: int = 10) -> dict:
        """Extract factor weights from recent decisions for a symbol"""
        relevant = [
            d for d in self.decisions[-limit:]
            if d.get("outputs", {}).get("symbol") == symbol
        ]

        if not relevant:
            return {"technical": 0.33, "sentiment": 0.33, "risk": 0.34}

        weights = {"technical": [], "sentiment": [], "risk": []}
        for d in relevant:
            factors = d.get("outputs", {}).get("factors", {})
            for key, val in factors.items():
                if key in weights:
                    weights[key].append(val)

        return {
            key: sum(vals) / len(vals) if vals else 0.33
            for key, vals in weights.items()
        }


class SignalGenerator:
    """Generate final trading signals with explanations"""

    def __init__(self):
        self.llm = OllamaLLM()
        self.explainer = ExplainabilityLogger()

    async def generate_signal(
        self,
        symbol: str,
        price: float,
        technical: TechnicalIndicators,
        sentiment: SentimentAnalysis,
        technical_analysis: dict,
        risk_checks: dict,
    ) -> TradeSignal:
        """Generate a comprehensive trading signal with explanation"""

        tech_weight = 0.35
        sentiment_weight = 0.35
        risk_weight = 0.30

        tech_signal = technical_analysis.get("confidence", 0.5)
        sentiment_score = abs(sentiment.overall_score)

        weighted_signal = (
            tech_signal * tech_weight
            + sentiment_score * sentiment_weight
            + risk_checks.get("approved", False) * risk_weight
        )

        if not risk_checks.get("approved", False):
            action = TradeAction.HOLD
            confidence = 0.3
        elif technical_analysis.get("signal") == "BUY" and sentiment.overall_score > 0:
            if weighted_signal > 0.6:
                action = TradeAction.BUY
                confidence = min(0.95, weighted_signal)
            else:
                action = TradeAction.HOLD
                confidence = weighted_signal
        elif technical_analysis.get("signal") == "SELL" and sentiment.overall_score < 0:
            if weighted_signal > 0.6:
                action = TradeAction.SELL
                confidence = min(0.95, weighted_signal)
            else:
                action = TradeAction.HOLD
                confidence = weighted_signal
        else:
            action = TradeAction.HOLD
            confidence = weighted_signal

        explanation = await self.llm.generate_explanation(
            symbol, action, confidence,
            technical.model_dump() if technical else {},
            sentiment.model_dump() if sentiment else {},
        )

        if not explanation or "Error" in explanation:
            explanation = self._generate_fallback_explanation(
                action, confidence, technical, sentiment
            )

        self.explainer.log_decision(
            agent_name="SignalGenerator",
            decision_type="FINAL_SIGNAL",
            inputs={
                "symbol": symbol,
                "price": price,
                "technical_signal": technical_analysis.get("signal"),
                "sentiment_score": sentiment.overall_score,
            },
            outputs={
                "symbol": symbol,
                "action": action.value,
                "confidence": confidence,
                "factors": {
                    "technical": tech_weight * tech_signal,
                    "sentiment": sentiment_weight * sentiment_score,
                    "risk": risk_weight if risk_checks.get("approved") else 0,
                },
            },
            reasoning=explanation,
            confidence=confidence,
        )

        return TradeSignal(
            symbol=symbol,
            action=action,
            confidence=confidence,
            timestamp=datetime.now(),
            price=price,
            factors={
                "technical": tech_weight * tech_signal,
                "sentiment": sentiment_weight * sentiment_score,
                "risk": risk_weight if risk_checks.get("approved") else 0,
            },
            explanation=explanation,
            agent_reasoning=[
                f"Technical Analysis: {technical_analysis.get('signal', 'HOLD')} "
                f"(confidence: {technical_analysis.get('confidence', 0):.2f})",
                f"Sentiment: {sentiment.overall_score:.2f} "
                f"(bullish: {sentiment.bullish_count}, bearish: {sentiment.bearish_count})",
                f"Risk Check: {'APPROVED' if risk_checks.get('approved') else 'REJECTED'}",
            ],
            technical_indicators=technical,
            sentiment=sentiment,
        )

    def _generate_fallback_explanation(
        self,
        action: TradeAction,
        confidence: float,
        technical: TechnicalIndicators,
        sentiment: SentimentAnalysis,
    ) -> str:
        """Generate explanation without LLM"""
        parts = [f"Signal: {action.value} with {confidence:.0%} confidence."]

        if technical.rsi:
            parts.append(f"RSI at {technical.rsi:.1f}.")

        if technical.macd_histogram is not None:
            direction = "bullish" if technical.macd_histogram > 0 else "bearish"
            parts.append(f"MACD histogram is {direction}.")

        parts.append(f"Sentiment score: {sentiment.overall_score:.2f}.")

        return " ".join(parts)

    def get_explanation_history(self) -> list[dict]:
        """Get explanation history for dashboard"""
        return self.explainer.get_decision_history()


signal_generator = SignalGenerator()
