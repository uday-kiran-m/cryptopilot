"""Chart components using Plotly."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional
import pandas as pd


class PriceChart:
    """Candlestick price chart component."""
    
    @staticmethod
    def render(ohlcv_data: pd.DataFrame, symbol: str = "BTCUSDT", height: int = 400):
        """Render a candlestick chart with volume."""
        if ohlcv_data is None or ohlcv_data.empty:
            st.info("No price data available. Configure API keys or use stubs.")
            return
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f'{symbol} Price', 'Volume')
        )
        
        fig.add_trace(
            go.Candlestick(
                x=ohlcv_data['timestamp'],
                open=ohlcv_data['open'],
                high=ohlcv_data['high'],
                low=ohlcv_data['low'],
                close=ohlcv_data['close'],
                name='OHLC',
                increasing_line_color='#0ecb81',
                decreasing_line_color='#ef4444',
            ),
            row=1, col=1
        )
        
        colors = ['#0ecb81' if ohlcv_data.iloc[i]['close'] >= ohlcv_data.iloc[i]['open'] else '#ef4444' 
                  for i in range(len(ohlcv_data))]
        
        fig.add_trace(
            go.Bar(
                x=ohlcv_data['timestamp'],
                y=ohlcv_data['volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.7
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=height,
            showlegend=False,
            xaxis_rangeslider_visible=False,
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        
        fig.update_xaxes(showgrid=True, gridcolor='#2a2a4a', row=2, col=1)
        fig.update_yaxes(showgrid=True, gridcolor='#2a2a4a', row=1, col=1)
        fig.update_yaxes(showgrid=True, gridcolor='#2a2a4a', row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)


class SentimentChart:
    """Sentiment visualization chart."""
    
    @staticmethod
    def render_bars(sentiment_data: Dict[str, float], title: str = "Sentiment Analysis"):
        """Render a horizontal bar chart for sentiment."""
        df = pd.DataFrame({
            'Source': list(sentiment_data.keys()),
            'Score': list(sentiment_data.values())
        })
        
        colors = []
        for score in df['Score']:
            if score > 0.6:
                colors.append('#22c55e')
            elif score < 0.4:
                colors.append('#ef4444')
            else:
                colors.append('#f59e0b')
        
        fig = px.bar(
            df, 
            y='Source', 
            x='Score',
            orientation='h',
            title=title,
            color='Score',
            color_continuous_scale=['#ef4444', '#f59e0b', '#22c55e'],
            range_color=[0, 1]
        )
        
        fig.update_layout(
            height=200,
            showlegend=False,
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_range=[0, 1],
        )
        
        fig.update_xaxes(showgrid=True, gridcolor='#2a2a4a')
        fig.update_yaxes(showgrid=False)
        
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_timeline(sentiment_history: List[Dict[str, Any]], title: str = "Sentiment Over Time"):
        """Render sentiment trend line chart."""
        if not sentiment_history:
            st.info("No sentiment history available.")
            return
        
        df = pd.DataFrame(sentiment_history)
        
        fig = px.line(
            df,
            x='timestamp',
            y='score',
            title=title,
            markers=True,
            color_discrete_sequence=['#0ecb81']
        )
        
        fig.update_layout(
            height=250,
            showlegend=False,
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        
        fig.update_xaxes(showgrid=True, gridcolor='#2a2a4a')
        fig.update_yaxes(showgrid=True, gridcolor='#2a2a4a', range=[0, 1])
        
        st.plotly_chart(fig, use_container_width=True)


class FactorChart:
    """Factor attribution visualization."""
    
    @staticmethod
    def render_attribution(factors: Dict[str, float], title: str = "Decision Factor Attribution"):
        """Render factor attribution as horizontal bars."""
        factor_names = {
            'technical': 'Technical Analysis',
            'sentiment': 'Market Sentiment',
            'risk': 'Risk Assessment',
        }
        
        display_names = [factor_names.get(k, k.title()) for k in factors.keys()]
        values = list(factors.values())
        
        colors = ['#3b82f6', '#8b5cf6', '#f59e0b']
        
        fig = go.Figure(go.Bar(
            y=display_names,
            x=values,
            orientation='h',
            marker_color=colors[:len(values)],
            text=[f"{v:.0%}" for v in values],
            textposition='outside',
        ))
        
        fig.update_layout(
            title=title,
            height=200,
            showlegend=False,
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_range=[0, 1],
        )
        
        fig.update_xaxes(showgrid=True, gridcolor='#2a2a4a', title='Weight')
        fig.update_yaxes(showgrid=False)
        
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_radar(factors: Dict[str, float], title: str = "Signal Profile"):
        """Render factor attribution as radar chart."""
        categories = [k.title() for k in factors.keys()]
        values = list(factors.values())
        values.append(values[0])
        categories.append(categories[0])
        
        fig = go.Figure(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            fillcolor='rgba(14, 203, 129, 0.3)',
            line_color='#0ecb81',
        ))
        
        fig.update_layout(
            title=title,
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    gridcolor='#2a2a4a',
                ),
                bgcolor='rgba(0,0,0,0)',
            ),
            showlegend=False,
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        
        st.plotly_chart(fig, use_container_width=True)


class PortfolioChart:
    """Portfolio visualization charts."""
    
    @staticmethod
    def render_pie(allocations: Dict[str, float], title: str = "Portfolio Distribution"):
        """Render portfolio allocation as pie chart."""
        fig = px.pie(
            values=list(allocations.values()),
            names=list(allocations.keys()),
            title=title,
            hole=0.4,
            color_discrete_sequence=['#0ecb81', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'],
        )
        
        fig.update_layout(
            height=300,
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_equity_curve(equity_history: List[Dict[str, Any]], title: str = "Equity Curve"):
        """Render equity curve over time."""
        if not equity_history:
            st.info("No equity history available.")
            return
        
        df = pd.DataFrame(equity_history)
        
        fig = px.line(
            df,
            x='timestamp',
            y='equity',
            title=title,
            color_discrete_sequence=['#0ecb81']
        )
        
        fig.update_layout(
            height=300,
            showlegend=False,
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        
        fig.update_xaxes(showgrid=True, gridcolor='#2a2a4a')
        fig.update_yaxes(showgrid=True, gridcolor='#2a2a4a')
        
        st.plotly_chart(fig, use_container_width=True)
