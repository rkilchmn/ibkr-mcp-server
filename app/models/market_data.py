"""Pydantic models for market data."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class BarData(BaseModel):
  """Historical bar data."""

  date: str = Field(..., description="Bar date/time")
  open: float = Field(..., description="Open price")
  high: float = Field(..., description="High price")
  low: float = Field(..., description="Low price")
  close: float = Field(..., description="Close price")
  volume: int = Field(..., description="Volume")
  wap: float | None = Field(None, description="Weighted average price")
  count: int | None = Field(None, description="Trade count")


class TickData(BaseModel):
  """Market tick data."""

  symbol: str = Field(..., description="Symbol")
  contract_id: int | None = Field(None, description="Contract ID")
  last: float | None = Field(None, description="Last price")
  close: float | None = Field(None, description="Close price")
  bid: float | None = Field(None, description="Bid price")
  ask: float | None = Field(None, description="Ask price")
  bid_size: int | None = Field(None, description="Bid size")
  ask_size: int | None = Field(None, description="Ask size")
  volume: int | None = Field(None, description="Volume")
  timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp")
  market_data_type: int | None = Field(None, description="Market data type")

  @field_validator('last', 'bid', 'ask')
  @classmethod
  def validate_price(cls, v):
    if v is None:
      return None
    # Check for NaN or infinity
    if isinstance(v, float) and (v != v or v == float('inf') or v == float('-inf')):
      return None
    return v

  @field_validator('bid_size', 'ask_size', 'volume')
  @classmethod
  def validate_size(cls, v):
    if v is None:
      return None
    # Check for NaN or infinity
    if isinstance(v, (int, float)) and (v != v or v == float('inf') or v == float('-inf')):
      return None
    if v < 0:
      return None
    return v


class HistoricalDataRequest(BaseModel):
  """Request for historical market data."""

  symbol: str = Field(..., description="Symbol")
  sec_type: str = Field(default="STK", description="Security type")
  exchange: str = Field(default="SMART", description="Exchange")
  currency: str = Field(default="USD", description="Currency")
  duration: str = Field(default="1 D", description="Duration (e.g., '1 D', '1 W', '1 M')")
  bar_size: str = Field(default="1 min", description="Bar size (e.g., '1 min', '5 mins', '1 hour', '1 day')")
  what_to_show: str = Field(default="TRADES", description="What to show (TRADES, MIDPOINT, BID, ASK)")
  use_rth: bool = Field(default=True, description="Use regular trading hours only")


class MarketDataRequest(BaseModel):
  """Request for real-time market data."""

  symbol: str = Field(..., description="Symbol")
  sec_type: str = Field(default="STK", description="Security type")
  exchange: str = Field(default="SMART", description="Exchange")
  currency: str = Field(default="USD", description="Currency")
  con_id: int | None = Field(None, description="Contract ID")
