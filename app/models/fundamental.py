"""Pydantic models for fundamental data."""
from datetime import date
from pydantic import BaseModel, Field


class Dividend(BaseModel):
  """Dividend information."""

  ex_date: str | None = Field(None, description="Ex-dividend date in YYYY-MM-DD format")
  pay_date: str | None = Field(None, description="Payment date in YYYY-MM-DD format")
  amount: float | None = Field(None, description="Dividend amount per share")


class EarningsEvent(BaseModel):
  """Earnings event information."""

  period: str | None = Field(None, description="Reporting period in YYYY-MM-DD format")
  estimate: float | None = Field(None, description="Estimated EPS")
  actual: float | None = Field(None, description="Actual EPS reported")


class FundamentalData(BaseModel):
  """Model for fundamental data returned from IBKR.

  Represents the parsed XML from IBKR's CalendarReport,
  ReportSnapshot, or other fundamental report types.
  """

  contract_id: int = Field(..., description="Contract ID")
  symbol: str = Field(..., description="Symbol")
  sec_type: str = Field(..., description="Security type")
  report_type: str = Field(..., description="Fundamental report type (e.g., CalendarReport)")

  # Earnings
  next_earnings_date: str | None = Field(
    None,
    description="Next earnings date in YYYY-MM-DD format",
  )
  earnings_estimate: float | None = Field(None, description="Estimated EPS for next earnings")
  earnings_actual: float | None = Field(None, description="Actual EPS for last earnings")
  earnings_history: list[EarningsEvent] = Field(
    default_factory=list,
    description="Historical earnings events",
  )

  # Dividends
  dividend_yield: float | None = Field(
    None,
    description="Trailing 12-month dividend yield as a decimal (e.g., 0.025 for 2.5%)",
  )
  next_dividend: Dividend | None = Field(None, description="Next dividend payment info")
  dividend_history: list[Dividend] = Field(
    default_factory=list,
    description="Historical dividend payments",
  )

  # Financial metrics
  pe_ratio: float | None = Field(None, description="Price-to-earnings ratio (TTM)")
  peg_ratio: float | None = Field(None, description="PEG ratio")
  price_to_book: float | None = Field(None, description="Price-to-book ratio")
  price_to_sales: float | None = Field(None, description="Price-to-sales ratio")
  enterprise_value: float | None = Field(None, description="Enterprise value")
  market_cap: float | None = Field(None, description="Market capitalization")

  # Company info
  industry: str | None = Field(None, description="Industry classification")
  sector: str | None = Field(None, description="Sector classification")
  full_name: str | None = Field(None, description="Full company name")
  description: str | None = Field(None, description="Company/business description")

  # Raw XML (for full fidelity)
  raw_xml: str | None = Field(
    None,
    description="Raw XML response from IBKR for full data access",
  )
