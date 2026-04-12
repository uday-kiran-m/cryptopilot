# CryptoPilot

An explainable multi-agentic AI crypto trading system that combines market data analysis, sentiment tracking, and technical indicators to generate trading signals with full transparency.

## Features

- **Multi-Agent Architecture**: Specialized agents for data fetching, sentiment analysis, technical analysis, risk management, and signal generation
- **Explainable AI**: Every decision is logged with full reasoning for audit trails
- **Paper Trading**: Practice trading without real money
- **Real-Time Dashboard**: Visual analytics with Streamlit
- **Multiple Data Sources**: Binance, Coinbase, CryptoPanic, CoinDesk

## Supported Cryptocurrencies

- Bitcoin (BTC)
- Ethereum (ETH)
- Solana (SOL)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or with optional dev dependencies:

```bash
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Optional - for real exchange data
BINANCE_API_KEY=your_binance_key
BINANCE_API_SECRET=your_binance_secret
COINBASE_API_KEY=your_coinbase_key
COINBASE_API_SECRET=your_coinbase_secret

# For news sentiment
CRYPTOPANIC_API_KEY=your_cryptopanic_key

# Ollama (required for LLM explanations)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### 3. Install & Start Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.2:3b

# Verify
ollama list
```

### 4. Run Analysis

```bash
# Single analysis
python -m src.main

# Continuous analysis (every 15 min)
python -m src.main --continuous

# Launch dashboard
python -m src.main --dashboard
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT                        │
└──────────────────────────┬───────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    ▼                      ▼                      ▼
┌─────────┐          ┌──────────┐           ┌─────────────┐
│  DATA   │          │SENTIMENT │           │TECHNICAL    │
│  AGENTS │          │  AGENT   │           │  ANALYST    │
│(BTC/ETH/│          │          │           │   AGENT     │
│  SOL)   │          │ News +   │           │             │
│         │          │ Votes    │           │RSI, MACD,   │
│ Price   │          │ Analysis │           │Bollinger    │
└────┬────┘          └────┬─────┘           └──────┬──────┘
     │                    │                        │
     └────────────────────┼────────────────────────┘
                          ▼
                ┌──────────────────┐
                │   RISK MANAGER   │
                │     AGENT        │
                │                  │
                │ Position sizing  │
                │ Stop loss/take   │
                └────────┬─────────┘
                         ▼
                ┌──────────────────┐
                │    SIGNAL +      │
                │   EXPLANATION    │
                └──────────────────┘
```

## Agents

| Agent | Role |
|-------|------|
| **Data Agents** | Fetch OHLCV data from Binance/Coinbase |
| **Sentiment Agent** | Analyze news from CryptoPanic & CoinDesk |
| **Technical Analyst** | Calculate RSI, MACD, Bollinger Bands |
| **Risk Manager** | Position sizing, stop-loss, exposure limits |
| **Signal Generator** | Final recommendation + LLM explanation |

## Dashboard Screenshots

The dashboard provides:
- Real-time trading signals with confidence scores
- Factor attribution charts (technical/sentiment/risk)
- Portfolio management with P&L tracking
- Audit logs with full decision reasoning

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `PAPER_TRADING` | `true` | Paper trading mode |
| `INITIAL_BALANCE` | `10000.0` | Starting balance |
| `MAX_POSITION_SIZE` | `0.1` | Max 10% per position |
| `STOP_LOSS_PERCENT` | `5.0` | 5% stop loss |
| `TAKE_PROFIT_PERCENT` | `10.0` | 10% take profit |
| `UPDATE_INTERVAL` | `900` | 15 min between cycles |

## API Keys

### Binance (Optional)
- Get keys at: https://www.binance.com/en/my/settings/api-management
- Public endpoints work without keys

### Coinbase (Optional)
- Get keys at: https://cdp.coinbase.com/
- Public endpoints work without keys

### CryptoPanic
- Free API key at: https://cryptopanic.com/
- Used for news sentiment

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint code
ruff check src/

# Type check
mypy src/
```

## Disclaimer

This software is for educational purposes only. Crypto trading carries significant risk of loss. Past performance does not guarantee future results. Do not invest more than you can afford to lose.

## License

MIT License - see LICENSE file
