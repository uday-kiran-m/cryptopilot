"""Trade queue monitoring page."""

from __future__ import annotations

import json
import random
from dataclasses import replace
from datetime import datetime, timedelta

import streamlit as st

from src.trading.simple_trade_engine import MarketSnapshot, TradeQueueEngine
from src.trading.simple_trade_market import IndicatorSnapshot


DEFAULT_TRADE_QUEUE_JSON = """[
  {
    "trade_id": "btc-breakout",
    "asset_name": "BTCUSDT",
    "entry_condition": "RSI > 45 AND EMA20 > EMA50",
    "exit_condition": "RSI < 35 OR EMA20 < EMA50",
    "target": 79000,
    "stop_loss": 74500,
    "position_size": 1000,
    "timeframe": "5m",
    "valid_until": "2026-04-22T23:59:59"
  },
  {
    "trade_id": "eth-trend",
    "asset_name": "ETHUSDT",
    "entry_condition": "EMA20 > EMA50 AND MACD > MACDsignal",
    "exit_condition": "EMA20 < EMA50 OR MACD < MACDsignal",
    "target": 4200,
    "stop_loss": 3600,
    "position_size": 700,
    "timeframe": "15m",
    "valid_until": "2026-04-22T23:59:59"
  }
]"""


def _ensure_queue_state() -> None:
    if "trade_queue_json" not in st.session_state:
        st.session_state.trade_queue_json = DEFAULT_TRADE_QUEUE_JSON
    if "trade_queue_engine" not in st.session_state:
        st.session_state.trade_queue_engine = TradeQueueEngine.from_json(
            st.session_state.trade_queue_json,
            portfolio_usd=100_000,
        )
    if "trade_queue_snapshots" not in st.session_state:
        st.session_state.trade_queue_snapshots = {}
    if "trade_queue_events" not in st.session_state:
        st.session_state.trade_queue_events = []


def _random_price_for_asset(asset_name: str) -> float:
    if asset_name == "BTCUSDT":
        return random.uniform(73000, 79000)
    if asset_name == "ETHUSDT":
        return random.uniform(3400, 4100)
    if asset_name == "SOLUSDT":
        return random.uniform(140, 220)
    return random.uniform(50, 500)


def _build_stub_snapshot(asset_name: str, timeframe: str) -> MarketSnapshot:
    price = _random_price_for_asset(asset_name)
    rsi = random.uniform(20, 80)
    ema20 = price * random.uniform(0.985, 1.015)
    ema50 = price * random.uniform(0.985, 1.015)
    macd = random.uniform(-15, 15)
    macd_signal = macd + random.uniform(-5, 5)
    middle = price * random.uniform(0.99, 1.01)
    spread = price * random.uniform(0.01, 0.03)

    indicators = IndicatorSnapshot(
        price=price,
        rsi=rsi,
        ema20=ema20,
        ema50=ema50,
        macd=macd,
        macd_signal=macd_signal,
        bollinger_upper=middle + spread,
        bollinger_middle=middle,
        bollinger_lower=middle - spread,
    )
    now = datetime.now()
    return MarketSnapshot(
        asset_name=asset_name,
        timeframe=timeframe,
        indicators=indicators,
        last_indicator_refresh=now,
        last_price_refresh=now,
    )


def _refresh_snapshots(engine: TradeQueueEngine, use_stubs: bool) -> dict[tuple[str, str], MarketSnapshot]:
    snapshots: dict[tuple[str, str], MarketSnapshot] = {}
    for asset_name, timeframe in engine.active_market_keys():
        if use_stubs:
            snapshots[(asset_name, timeframe)] = _build_stub_snapshot(asset_name, timeframe)
            continue

        candles = engine.fetch_binance_klines(asset_name, interval=timeframe, limit=50)
        indicators = engine.calculate_indicators(candles)
        now = datetime.now()
        snapshots[(asset_name, timeframe)] = MarketSnapshot(
            asset_name=asset_name,
            timeframe=timeframe,
            indicators=indicators,
            last_indicator_refresh=now,
            last_price_refresh=now,
        )
    return snapshots


def _event_rows(events: list[dict]) -> list[dict]:
    rows = []
    for event in events:
        rows.append(
            {
                "time": datetime.now().strftime("%H:%M:%S"),
                "trade_id": event.get("trade_id"),
                "asset": event.get("asset_name"),
                "timeframe": event.get("timeframe"),
                "action": event.get("action"),
                "status": event.get("status"),
                "price": None if event.get("indicators") is None else round(event["indicators"].price, 2),
                "pnl_usd": event.get("pnl_usd"),
                "reason": event.get("reason"),
            }
        )
    return rows


def render_trade_queue_page(symbol: str = "BTCUSDT", use_stubs: bool = True):
    _ensure_queue_state()

    st.header("Queue Monitor")
    st.markdown("Review queued trades, process entry and exit checks, and inspect UI-ready event payloads.")

    col1, col2 = st.columns([2, 1])

    with col1:
        updated_json = st.text_area(
            "Trade Queue JSON",
            value=st.session_state.trade_queue_json,
            height=260,
            key="trade_queue_json_editor",
        )

    with col2:
        st.markdown("### Actions")

        if st.button("Load Queue", use_container_width=True):
            try:
                st.session_state.trade_queue_json = updated_json
                st.session_state.trade_queue_engine = TradeQueueEngine.from_json(
                    updated_json,
                    portfolio_usd=100_000,
                )
                st.session_state.trade_queue_snapshots = {}
                st.session_state.trade_queue_events = []
                st.success("Queue loaded.")
            except Exception as exc:
                st.error(f"Could not load queue: {exc}")

        if st.button("Process Once", use_container_width=True, type="primary"):
            try:
                engine = st.session_state.trade_queue_engine
                snapshots = _refresh_snapshots(engine, use_stubs=use_stubs)
                events = engine.process_queue(snapshots=snapshots, now=datetime.now())
                st.session_state.trade_queue_snapshots = snapshots
                st.session_state.trade_queue_events = _event_rows(events) + st.session_state.trade_queue_events[:19]
                st.success("Queue processed.")
            except Exception as exc:
                st.error(f"Could not process queue: {exc}")

        if st.button("Reset Demo", use_container_width=True):
            st.session_state.trade_queue_json = DEFAULT_TRADE_QUEUE_JSON
            st.session_state.trade_queue_engine = TradeQueueEngine.from_json(
                DEFAULT_TRADE_QUEUE_JSON,
                portfolio_usd=100_000,
            )
            st.session_state.trade_queue_snapshots = {}
            st.session_state.trade_queue_events = []
            st.rerun()

        st.caption("`Use AI Stubs` in the sidebar controls whether this page uses live market fetches or local stub snapshots.")

    engine: TradeQueueEngine = st.session_state.trade_queue_engine
    summary = engine.queue_summary()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Queue", len(summary["queued_trades"]))
    with col2:
        st.metric("Cash", f"${summary['portfolio']['cash_usd']:,.2f}")
    with col3:
        st.metric("Open Positions", len(summary["portfolio"]["positions"]))
    with col4:
        st.metric("Trade Log", summary["portfolio"]["trade_count"])

    st.divider()

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown("### Active Trades")
        if summary["queued_trades"]:
            st.dataframe(summary["queued_trades"], use_container_width=True)
        else:
            st.info("No active trades in queue.")

    with col2:
        st.markdown("### Portfolio")
        st.json(summary["portfolio"], expanded=False)

    st.divider()

    st.markdown("### Recent Events")
    if st.session_state.trade_queue_events:
        st.dataframe(st.session_state.trade_queue_events, use_container_width=True)
    else:
        st.info("Process the queue once to populate event output.")

    st.markdown("### Last Snapshots")
    if st.session_state.trade_queue_snapshots:
        snapshot_payload = {}
        for key, snapshot in st.session_state.trade_queue_snapshots.items():
            snapshot_payload[f"{key[0]}:{key[1]}"] = {
                "price": snapshot.indicators.price,
                "rsi": snapshot.indicators.rsi,
                "ema20": snapshot.indicators.ema20,
                "ema50": snapshot.indicators.ema50,
                "macd": snapshot.indicators.macd,
                "macd_signal": snapshot.indicators.macd_signal,
                "bollinger_upper": snapshot.indicators.bollinger_upper,
                "bollinger_middle": snapshot.indicators.bollinger_middle,
                "bollinger_lower": snapshot.indicators.bollinger_lower,
                "last_indicator_refresh": snapshot.last_indicator_refresh.isoformat(),
            }
        st.json(snapshot_payload, expanded=False)
    else:
        st.info("No snapshots available yet.")
