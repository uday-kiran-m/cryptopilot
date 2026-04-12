import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Exchange APIs
    binance_api_key: str = Field(default="", validation_alias="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", validation_alias="BINANCE_API_SECRET")
    coinbase_api_key: str = Field(default="", validation_alias="COINBASE_API_KEY")
    coinbase_api_secret: str = Field(default="", validation_alias="COINBASE_API_SECRET")

    # News APIs
    cryptopanic_api_key: str = Field(default="", validation_alias="CRYPTOPANIC_API_KEY")

    # Ollama Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(default="llama3.2:3b", validation_alias="OLLAMA_MODEL")
    ollama_embed_model: str = Field(
        default="nomic-embed-text", validation_alias="OLLAMA_EMBED_MODEL"
    )

    # Application Settings
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    paper_trading: bool = Field(default=True, validation_alias="PAPER_TRADING")
    initial_balance: float = Field(
        default=10000.0, validation_alias="INITIAL_BALANCE"
    )
    max_position_size: float = Field(
        default=0.1, validation_alias="MAX_POSITION_SIZE"
    )
    stop_loss_percent: float = Field(
        default=5.0, validation_alias="STOP_LOSS_PERCENT"
    )
    take_profit_percent: float = Field(
        default=10.0, validation_alias="TAKE_PROFIT_PERCENT"
    )

    # Trading Pairs
    symbols: list[str] = Field(
        default=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        validation_alias="SYMBOLS",
    )

    # Update Frequency
    update_interval: int = Field(
        default=900, validation_alias="UPDATE_INTERVAL"
    )

    @property
    def data_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "data"

    @property
    def logs_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "logs"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "cryptopilot.db"

    def get_symbol_display(self, symbol: str) -> tuple[str, str]:
        """Convert symbol like BTCUSDT to (base, quote)"""
        for quote in ["USDT", "USD", "USDC"]:
            if symbol.endswith(quote):
                base = symbol.replace(quote, "")
                return base, quote
        return symbol[:3], symbol[3:]

    def get_coinbase_product_id(self, symbol: str) -> str:
        """Convert Binance symbol to Coinbase product ID"""
        base, quote = self.get_symbol_display(symbol)
        return f"{base}-{quote}"


settings = Settings()
