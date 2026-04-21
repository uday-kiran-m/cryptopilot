"""Trading Cycle page - Brain agent integration."""

import streamlit as st
import asyncio
import sys
import os
from datetime import datetime
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.dashboard.shared.state import SessionState


def init_brain_orchestrator():
    """Initialize the brain orchestrator."""
    try:
        from brain.src.agents.orchestrator import get_orchestrator

        orchestrator = get_orchestrator(
            initial_balance=SessionState.get('initial_balance', 10000.0),
            symbol=SessionState.get('trading_symbol', 'BTCUSDT'),
            timeframe=SessionState.get('timeframe', '4h'),
        )

        if not orchestrator._initialized:
            with st.spinner("Initializing Brain agents..."):
                orchestrator.initialize()

        SessionState.set('brain_initialized', True)
        SessionState.set('brain_orchestrator', orchestrator)

        return orchestrator
    except Exception as e:
        st.error(f"Error initializing brain: {e}")
        return None


def run_analysis(orchestrator):
    """Run a single analysis cycle."""
    try:
        result = asyncio.run(orchestrator.run_analysis_cycle())

        result_dict = {
            'timestamp': result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat(),
            'symbol': result.symbol,
            'signal': result.analyst_signal.signal,
            'confidence': result.analyst_signal.confidence,
            'strategy_used': result.analyst_signal.strategy_used,
            'reasoning': result.analyst_signal.reasoning,
            'internal_monologue': result.analyst_signal.internal_monologue,
            'sentiment_score': result.sentiment_score,
            'risk_assessment': {
                'signal': result.risk_assessment.signal,
                'is_approved': result.risk_assessment.is_approved,
                'position_size': result.risk_assessment.position_size,
                'stop_loss': result.risk_assessment.stop_loss,
                'take_profit': result.risk_assessment.target,
                'audit_summary': result.risk_assessment.audit_summary,
            },
            'recommendation': None,
        }

        if result.recommendation:
            result_dict['recommendation'] = {
                'signal': result.recommendation.signal,
                'entry_price': result.recommendation.entry_price,
                'position_size': result.recommendation.position_size,
                'stop_loss': result.recommendation.stop_loss,
                'take_profit': result.recommendation.take_profit,
            }

        if result.market_data:
            result_dict['market_data'] = {
                'price': result.market_data.snapshot.close if result.market_data.snapshot else 0,
                'rsi': result.market_data.rsi.current if result.market_data.rsi else 0,
                'atr': result.market_data.volatility.atr if result.market_data.volatility else 0,
                'market_structure': result.market_data.trends.market_structure if result.market_data.trends else '',
            }

        SessionState.set_brain_result(result_dict)

        portfolio = orchestrator.get_portfolio()
        SessionState.set_portfolio({
            'balance': portfolio.balance,
            'total_value': portfolio.total_value,
            'total_pnl': portfolio.total_pnl,
            'positions': {k: {'quantity': v.quantity, 'entry_price': v.entry_price, 'current_price': v.current_price}
                        for k, v in portfolio.positions.items()},
        })

        return result_dict

    except Exception as e:
        st.error(f"Error running analysis: {e}")
        import traceback
        traceback.print_exc()
        return None


def render_trading_cycle_page():
    """Render the Trading Cycle page."""
    st.markdown("""
    <div class="main-header">
        <div class="header-title">Trading <span>Cycle</span></div>
        <div class="header-subtitle">AI-powered trading analysis with brain agents</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("### Configuration")

        symbol = st.selectbox(
            "Trading Symbol",
            options=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            index=0,
        )
        SessionState.set('trading_symbol', symbol)

        timeframe = st.selectbox(
            "Timeframe",
            options=["1h", "4h", "1d"],
            index=1,
        )
        SessionState.set('timeframe', timeframe)

        initial_balance = st.number_input(
            "Initial Balance ($)",
            min_value=1000.0,
            value=10000.0,
            step=1000.0,
        )
        SessionState.set('initial_balance', initial_balance)

        st.divider()

        st.markdown("### Actions")

        init_button = st.button(
            "🔧 Initialize Brain",
            use_container_width=True,
            disabled=SessionState.get('brain_initialized', False),
        )

        if init_button:
            orchestrator = init_brain_orchestrator()
            if orchestrator:
                st.success("Brain initialized successfully!")

        analyze_button = st.button(
            "🎯 Run Analysis",
            type="primary",
            use_container_width=True,
        )

        result = None
        if analyze_button:
            with st.spinner("Running analysis cycle..."):
                orchestrator = SessionState.get('brain_orchestrator')
                if not orchestrator:
                    orchestrator = init_brain_orchestrator()

                if orchestrator:
                    result = run_analysis(orchestrator)

    with col2:
        st.markdown("### Analysis Results")

        last_result = SessionState.get_brain_result()

        if last_result:
            result = last_result

        if result:
            signal = result.get('signal', 'HOLD')
            confidence = result.get('confidence', 0)

            col1, col2, col3 = st.columns(3)

            with col1:
                badge_class = "signal-buy" if signal == "BUY" else "signal-sell" if signal == "SELL" else "signal-hold"
                st.markdown(f'<span class="signal-badge {badge_class}" style="font-size: 1.5rem; padding: 10px 24px;">{signal}</span>',
                           unsafe_allow_html=True)

            with col2:
                st.metric("Confidence", f"{confidence:.1%}")

            with col3:
                sentiment = result.get('sentiment_score', 0.5)
                sentiment_label = "Bullish" if sentiment > 0.6 else "Bearish" if sentiment < 0.4 else "Neutral"
                st.metric("Sentiment", sentiment_label, delta=f"{sentiment:.0%}")

            st.divider()

            if result.get('market_data'):
                md = result['market_data']
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Price", f"${md.get('price', 0):,.2f}")
                with col2:
                    st.metric("RSI", f"{md.get('rsi', 0):.1f}")
                with col3:
                    st.metric("ATR", f"{md.get('atr', 0):.2f}")
                with col4:
                    st.metric("Structure", md.get('market_structure', 'N/A'))

            st.divider()

            st.markdown("#### Strategy & Reasoning")
            st.markdown(f"**Strategy:** {result.get('strategy_used', 'N/A')}")
            st.markdown(f"**Reasoning:** {result.get('reasoning', 'No reasoning available')}")

            with st.expander("View Internal Monologue"):
                st.text(result.get('internal_monologue', 'No internal monologue available'))

            if result.get('risk_assessment'):
                ra = result['risk_assessment']
                st.divider()

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Position Size", f"${ra.get('position_size', 0):,.2f}")
                with col2:
                    st.metric("Stop Loss", f"${ra.get('stop_loss', 0):,.2f}")
                with col3:
                    st.metric("Take Profit", f"${ra.get('take_profit', 0):,.2f}")

                st.markdown(f"**Risk Approved:** {'✅ Yes' if ra.get('is_approved') else '❌ No'}")
                st.markdown(f"**Audit Summary:** {ra.get('audit_summary', 'N/A')}")

            if result.get('recommendation'):
                rec = result['recommendation']
                st.divider()

                st.markdown("#### Trade Recommendation")
                st.markdown(f"**Signal:** {rec.get('signal')}")
                st.markdown(f"**Entry Price:** ${rec.get('entry_price', 0):,.2f}")
                st.markdown(f"**Position Size:** ${rec.get('position_size', 0):,.2f}")
                st.markdown(f"**Stop Loss:** ${rec.get('stop_loss', 0):,.2f}")
                st.markdown(f"**Take Profit:** ${rec.get('take_profit', 0):,.2f}")

        else:
            st.info("Run an analysis to see results")
            st.markdown("""
            ### How it works:
            1. **Initialize Brain** - Sets up the knowledge base and agents
            2. **Run Analysis** - Executes one complete trading cycle:
               - Fetches live market data (55 candles, 4h timeframe)
               - Analyzes sentiment (stub returns 0.5)
               - Generates trading signal via LLM
               - Evaluates risk and creates trade recommendation
            """)

    st.divider()

    portfolio = SessionState.get_portfolio()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Balance", f"${portfolio.get('balance', 0):,.2f}")
    with col2:
        st.metric("Total Value", f"${portfolio.get('total_value', 0):,.2f}")
    with col3:
        pnl = portfolio.get('total_pnl', 0)
        color = "normal" if pnl >= 0 else "inverse"
        st.metric("Total P&L", f"${pnl:,.2f}", delta_color=color)
    with col4:
        positions = portfolio.get('positions', {})
        st.metric("Open Positions", len(positions))

    if positions:
        st.markdown("#### Open Positions")
        for symbol, pos in positions.items():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.markdown(f"**{symbol}**")
                with col2:
                    st.caption(f"Qty: {pos.get('quantity', 0):.4f}")
                with col3:
                    st.caption(f"Entry: ${pos.get('entry_price', 0):,.2f}")
                with col4:
                    current = pos.get('current_price', 0)
                    entry = pos.get('entry_price', 1)
                    pnl_pct = (current - entry) / entry * 100
                    color = "green" if pnl_pct >= 0 else "red"
                    st.markdown(f":{color}[{pnl_pct:+.1f}%]")
                with col5:
                    st.caption(f"Current: ${current:,.2f}")
