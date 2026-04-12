"""Audit analytics dashboard page."""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random
import json

from src.dashboard.shared.utils import action_badge, format_timestamp, time_ago
from src.dashboard.components.charts import PortfolioChart
from src.core.models import TradeAction


def generate_stub_audit_logs(symbol: str = None, count: int = 50) -> List[Dict[str, Any]]:
    """Generate realistic audit log entries."""
    logs = []
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    actions = list(TradeAction)
    
    for i in range(count):
        symbol = symbol or random.choice(symbols)
        action = random.choice(actions)
        price = random.uniform(45000, 65000) if 'BTC' in symbol else random.uniform(2500, 3500)
        
        factors = {
            'technical': random.uniform(0.3, 0.85),
            'sentiment': random.uniform(0.25, 0.80),
            'risk': random.uniform(0.30, 0.75),
        }
        
        is_winning = random.random() > 0.4
        profit_loss = random.uniform(50, 500) if is_winning else random.uniform(-300, -50)
        
        outcomes = ['pending', 'win', 'loss', 'breakeven']
        outcome_weights = [0.2, 0.4, 0.3, 0.1]
        outcome = random.choices(outcomes, weights=outcome_weights)[0]
        
        if outcome == 'pending':
            profit_loss = None
        
        logs.append({
            'id': 1000 + i,
            'timestamp': datetime.now() - timedelta(hours=i * 6 + random.randint(0, 5)),
            'symbol': symbol,
            'action': action.value,
            'confidence': random.uniform(0.55, 0.92),
            'price': price,
            'factors': factors,
            'explanation': f"Signal generated with {factors['technical']:.0%} technical weight, "
                          f"{factors['sentiment']:.0%} sentiment weight, {factors['risk']:.0%} risk weight.",
            'outcome': outcome,
            'profit_loss': profit_loss,
        })
    
    return sorted(logs, key=lambda x: x['timestamp'], reverse=True)


def calculate_audit_stats(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate audit statistics."""
    total = len(logs)
    if total == 0:
        return {}
    
    completed = [l for l in logs if l.get('outcome') in ['win', 'loss', 'breakeven']]
    wins = len([l for l in completed if l.get('outcome') == 'win'])
    losses = len([l for l in completed if l.get('outcome') == 'loss'])
    
    total_pnl = sum(l.get('profit_loss', 0) or 0 for l in logs)
    
    avg_confidence = sum(l.get('confidence', 0) for l in logs) / total
    
    return {
        'total_signals': total,
        'wins': wins,
        'losses': losses,
        'pending': total - len(completed),
        'win_rate': wins / len(completed) if completed else 0,
        'total_pnl': total_pnl,
        'avg_confidence': avg_confidence,
    }


def render_audit_page(symbol: str = "BTCUSDT", use_stubs: bool = True):
    """Render the audit analytics page."""
    st.header("📊 Audit & Analytics")
    st.markdown("Complete audit trail of trading decisions with performance analytics")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        symbol_filter = st.multiselect(
            "Symbols",
            options=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            default=["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        )
        
        action_filter = st.multiselect(
            "Actions",
            options=["BUY", "SELL", "HOLD"],
            default=["BUY", "SELL", "HOLD"]
        )
        
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now() - timedelta(days=7), datetime.now())
        )
        
        outcome_filter = st.multiselect(
            "Outcome",
            options=["win", "loss", "breakeven", "pending"],
            default=["win", "loss", "breakeven", "pending"]
        )
        
        if st.button("🔄 Apply Filters", use_container_width=True):
            st.rerun()
        
        st.divider()
        
        if st.button("📥 Export CSV", use_container_width=True):
            st.info("CSV export would be generated here")
        
        if st.button("📋 Export JSON", use_container_width=True):
            logs = generate_stub_audit_logs()
            json_data = json.dumps(logs, indent=2, default=str)
            st.download_button(
                label="Download JSON",
                data=json_data,
                file_name=f"audit_export_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )
    
    with col2:
        all_logs = generate_stub_audit_logs()
        
        if symbol_filter:
            all_logs = [l for l in all_logs if l['symbol'] in symbol_filter]
        if action_filter:
            all_logs = [l for l in all_logs if l['action'] in action_filter]
        if outcome_filter:
            all_logs = [l for l in all_logs if l.get('outcome', 'pending') in outcome_filter]
        
        stats = calculate_audit_stats(all_logs)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Signals", stats.get('total_signals', 0))
        with col2:
            win_rate = stats.get('win_rate', 0)
            st.metric("Win Rate", f"{win_rate:.1%}", 
                      delta="Profitable" if win_rate > 0.5 else "Below 50%")
        with col3:
            st.metric("Wins", stats.get('wins', 0))
        with col4:
            st.metric("Losses", stats.get('losses', 0))
        with col5:
            pnl = stats.get('total_pnl', 0)
            st.metric("Total P&L", f"${pnl:,.2f}", 
                      delta="green" if pnl > 0 else "red")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Win/Loss Distribution")
            
            outcome_counts = {
                'Win': stats.get('wins', 0),
                'Loss': stats.get('losses', 0),
                'Pending': stats.get('pending', 0),
            }
            
            for outcome, count in outcome_counts.items():
                if count > 0:
                    pct = count / stats.get('total_signals', 1) * 100
                    color = "green" if outcome == "Win" else "red" if outcome == "Loss" else "gray"
                    st.markdown(f"**{outcome}**: {count} ({pct:.1f}%)")
                    st.progress(count / stats.get('total_signals', 1), 
                               text=f"{pct:.1f}%",
                               )
        
        with col2:
            st.markdown("### Factor Effectiveness")
            
            factor_stats = {
                'Technical': random.uniform(0.55, 0.75),
                'Sentiment': random.uniform(0.45, 0.65),
                'Risk': random.uniform(0.50, 0.70),
            }
            
            for factor, effectiveness in factor_stats.items():
                st.markdown(f"**{factor}**: {effectiveness:.0%}")
                color = "#0ecb81" if effectiveness > 0.5 else "#f59e0b"
                st.markdown(f"""
                <div style="background: #2a2a4a; border-radius: 4px; overflow: hidden; margin: 4px 0;">
                    <div style="width: {effectiveness*100}%; background: {color}; padding: 4px 0;"></div>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        st.markdown("### Decision Timeline")
        
        for log in all_logs[:10]:
            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 2, 1, 1])
                
                with col1:
                    st.caption(format_timestamp(log['timestamp']))
                with col2:
                    st.caption(log['symbol'])
                with col3:
                    st.markdown(action_badge(log['action']), unsafe_allow_html=True)
                with col4:
                    st.caption(log['explanation'][:80] + "...")
                with col5:
                    outcome = log.get('outcome', 'pending')
                    if outcome == 'win':
                        st.markdown(":green[Win]")
                    elif outcome == 'loss':
                        st.markdown(":red[Loss]")
                    else:
                        st.markdown(":gray[Pending]")
                with col6:
                    if log.get('profit_loss'):
                        pnl = log['profit_loss']
                        color = "green" if pnl > 0 else "red"
                        st.markdown(f":{color}[${pnl:+.0f}]")
                
                st.divider()
        
        with st.expander("View All Decisions"):
            for log in all_logs[10:]:
                col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 3, 1])
                
                with col1:
                    st.caption(format_timestamp(log['timestamp']))
                with col2:
                    st.caption(log['symbol'])
                with col3:
                    st.markdown(action_badge(log['action']), unsafe_allow_html=True)
                with col4:
                    st.caption(log['explanation'][:100])
                with col5:
                    if log.get('profit_loss'):
                        pnl = log['profit_loss']
                        st.caption(f"${pnl:+.0f}")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Performance by Symbol")
            
            symbol_stats = {}
            for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
                sym_logs = [l for l in all_logs if l['symbol'] == sym]
                completed = [l for l in sym_logs if l.get('outcome') in ['win', 'loss']]
                wins = len([l for l in completed if l.get('outcome') == 'win'])
                win_rate = wins / len(completed) if completed else 0
                pnl = sum(l.get('profit_loss', 0) or 0 for l in sym_logs)
                
                symbol_stats[sym] = {
                    'signals': len(sym_logs),
                    'win_rate': win_rate,
                    'pnl': pnl,
                }
            
            for sym, data in symbol_stats.items():
                st.markdown(f"**{sym}**")
                st.markdown(f"  Signals: {data['signals']} | Win Rate: {data['win_rate']:.1%} | P&L: ${data['pnl']:+.2f}")
        
        with col2:
            st.markdown("### Confidence Distribution")
            
            confidence_buckets = {
                '55-65%': 0,
                '65-75%': 0,
                '75-85%': 0,
                '85-95%': 0,
            }
            
            for log in all_logs:
                conf = log.get('confidence', 0) * 100
                if conf < 65:
                    confidence_buckets['55-65%'] += 1
                elif conf < 75:
                    confidence_buckets['65-75%'] += 1
                elif conf < 85:
                    confidence_buckets['75-85%'] += 1
                else:
                    confidence_buckets['85-95%'] += 1
            
            for bucket, count in confidence_buckets.items():
                pct = count / len(all_logs) if all_logs else 0
                st.markdown(f"**{bucket}**: {count} signals ({pct:.1%})")
                st.progress(pct)
