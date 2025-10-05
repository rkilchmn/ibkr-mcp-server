"""Pydantic models for account data."""
from decimal import Decimal
from pydantic import BaseModel, Field


class AccountSummary(BaseModel):
  """Account summary information."""

  account: str = Field(..., description="Account ID")
  tag: str = Field(..., description="Summary tag")
  value: str = Field(..., description="Summary value")
  currency: str = Field(..., description="Currency")


class AccountValue(BaseModel):
  """Account value information."""

  account: str = Field(..., description="Account")
  key: str = Field(..., description="Value key")
  value: str = Field(..., description="Value")
  currency: str = Field(..., description="Currency")


class Position(BaseModel):
  """Position information."""

  account: str = Field(..., description="Account")
  symbol: str = Field(..., description="Symbol")
  sec_type: str = Field(..., description="Security type")
  exchange: str = Field(..., description="Exchange")
  currency: str = Field(..., description="Currency")
  position: float = Field(..., description="Position size")
  avg_cost: float = Field(..., description="Average cost")
  market_price: float | None = Field(None, description="Current market price")
  market_value: float | None = Field(None, description="Market value")
  unrealized_pnl: float | None = Field(None, description="Unrealized P&L")
  realized_pnl: float | None = Field(None, description="Realized P&L")
  contract_id: int | None = Field(None, description="Contract ID")
