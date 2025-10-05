"""Pydantic models for trading operations."""
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class OrderAction(str, Enum):
  """Order action types."""
  BUY = "BUY"
  SELL = "SELL"


class OrderType(str, Enum):
  """Order types."""
  MARKET = "MKT"
  LIMIT = "LMT"
  STOP = "STP"
  STOP_LIMIT = "STP LMT"
  TRAIL = "TRAIL"
  TRAIL_LIMIT = "TRAIL LIMIT"


class OrderStatus(str, Enum):
  """Order status types."""
  PENDING_SUBMIT = "PendingSubmit"
  PENDING_CANCEL = "PendingCancel"
  PRE_SUBMITTED = "PreSubmitted"
  SUBMITTED = "Submitted"
  CANCELLED = "Cancelled"
  FILLED = "Filled"
  INACTIVE = "Inactive"
  PENDING_REJECT = "PendingReject"
  REJECTED = "Rejected"


class TimeInForce(str, Enum):
  """Time in force types."""
  DAY = "DAY"
  GTC = "GTC"
  IOC = "IOC"
  GTD = "GTD"


class SecType(str, Enum):
  """Security types."""
  STOCK = "STK"
  OPTION = "OPT"
  FUTURE = "FUT"
  FOREX = "CASH"
  INDEX = "IND"
  CFD = "CFD"
  BOND = "BOND"
  WARRANT = "WAR"
  COMMODITY = "CMDTY"


class ContractRequest(BaseModel):
  """Contract information for trading."""

  symbol: str = Field(..., description="Contract symbol")
  sec_type: SecType = Field(..., description="Security type")
  exchange: str = Field(default="SMART", description="Exchange")
  currency: str = Field(default="USD", description="Currency")
  local_symbol: str | None = Field(None, description="Local symbol")
  con_id: int | None = Field(None, description="Contract ID")

  # Options specific
  strike: float | None = Field(None, description="Strike price for options")
  right: str | None = Field(None, description="Right (C/P) for options")
  expiry: str | None = Field(None, description="Expiry date (YYYYMMDD)")

  # Futures specific
  last_trade_date: str | None = Field(None, description="Last trade date for futures")
  multiplier: int | None = Field(None, description="Contract multiplier")


class OrderRequest(BaseModel):
  """Order information for placement."""

  action: OrderAction = Field(..., description="Order action (BUY/SELL)")
  total_quantity: float = Field(..., description="Total quantity", gt=0)
  order_type: OrderType = Field(..., description="Order type")
  lmt_price: float | None = Field(None, description="Limit price")
  aux_price: float | None = Field(None, description="Auxiliary price (stop price)")
  time_in_force: TimeInForce = Field(default=TimeInForce.DAY, description="Time in force")

  # Optional parameters
  good_after_time: str | None = Field(None, description="Good after time")
  good_till_date: str | None = Field(None, description="Good till date")
  outside_rth: bool = Field(default=False, description="Allow outside regular trading hours")
  hidden: bool = Field(default=False, description="Hidden order")

  @field_validator('total_quantity')
  @classmethod
  def validate_quantity(cls, v):
    if v <= 0:
      raise ValueError('Quantity must be positive')
    return v


class PlaceOrderRequest(BaseModel):
  """Request to place an order."""

  contract: ContractRequest = Field(..., description="Contract to trade")
  order: OrderRequest = Field(..., description="Order details")


class OrderResponse(BaseModel):
  """Response from order placement."""

  order_id: int = Field(..., description="Order ID")
  status: str = Field(..., description="Order status")
  symbol: str = Field(..., description="Symbol")
  action: str = Field(..., description="Action")
  quantity: float = Field(..., description="Quantity")
  filled: float = Field(default=0, description="Filled quantity")
  remaining: float = Field(default=0, description="Remaining quantity")
  avg_fill_price: float | None = Field(None, description="Average fill price")


class OrderExecution(BaseModel):
  """Order execution information."""

  exec_id: str = Field(..., description="Execution ID")
  order_id: int = Field(..., description="Order ID")
  symbol: str = Field(..., description="Symbol")
  side: str = Field(..., description="Side (BOT/SLD)")
  shares: float = Field(..., description="Executed shares")
  price: float = Field(..., description="Execution price")
  cum_qty: float = Field(..., description="Cumulative quantity")
  avg_price: float = Field(..., description="Average price")
  time: str = Field(..., description="Execution time")


class OpenOrder(BaseModel):
  """Open order information."""

  order_id: int = Field(..., description="Order ID")
  symbol: str = Field(..., description="Symbol")
  sec_type: str = Field(..., description="Security type")
  action: str = Field(..., description="Action")
  quantity: float = Field(..., description="Total quantity")
  order_type: str = Field(..., description="Order type")
  status: str = Field(..., description="Order status")
  limit_price: float | None = Field(None, description="Limit price")
  aux_price: float | None = Field(None, description="Auxiliary price")
  filled: float = Field(..., description="Filled quantity")
  remaining: float = Field(..., description="Remaining quantity")
  avg_fill_price: float | None = Field(None, description="Average fill price")
