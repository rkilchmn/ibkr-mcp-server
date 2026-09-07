"""Fundamental data tools."""
from fastapi import Query
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models import FundamentalData


CONTRACT_ID_QUERY = Query(default=None, description="IBKR contract ID. If provided, symbol lookup is skipped.")
SYMBOL_QUERY = Query(default=None, description="Symbol to look up (e.g., AAPL). Required if contract_id not provided.")
SEC_TYPE_QUERY = Query(default="STK", description="Security type (STK, OPT, FUT, etc.)")
EXCHANGE_QUERY = Query(default=None, description="Exchange (e.g., SMART, ISLAND)")
CURRENCY_QUERY = Query(default=None, description="Currency (e.g., USD)")
REPORT_TYPE_QUERY = Query(default="CalendarReport", description="Fundamental report type: ReportsFinSummary, ReportsOwnership, ReportSnapshot, ReportsFinStatements, RESC, CalendarReport")


@ibkr_router.get(
  "/fundamental",
  operation_id="get_fundamental_data",
  response_model=FundamentalData,
)
async def get_fundamental_data(
  contract_id: int | None = CONTRACT_ID_QUERY,
  symbol: str | None = SYMBOL_QUERY,
  sec_type: str = SEC_TYPE_QUERY,
  exchange: str | None = EXCHANGE_QUERY,
  currency: str | None = CURRENCY_QUERY,
  report_type: str = REPORT_TYPE_QUERY,
) -> FundamentalData:
  """Get fundamental data for a contract.

  Retrieves fundamental data from IBKR including earnings dates, dividend
  information, and financial metrics. The `CalendarReport` type provides
  earnings calendar and dividend data. `ReportSnapshot` and `ReportsFinSummary`
  provide financial ratios like P/E, dividend yield, etc.

  Args:
    contract_id: IBKR contract ID. If provided, symbol lookup is skipped.
    symbol: Symbol to look up (e.g., AAPL). Required if contract_id not provided.
    sec_type: Security type (STK, OPT, FUT, etc.).
    exchange: Exchange (e.g., SMART, ISLAND).
    currency: Currency (e.g., USD).
    report_type: Fundamental report type. Options:
      - CalendarReport: Earnings dates, dividend calendar
      - ReportsFinSummary: Financial summary (P/E, revenue, etc.)
      - ReportSnapshot: Company snapshot (ratios, dividend yield)
      - ReportsFinStatements: Full financial statements
      - RESC: Analyst estimates
      - ReportsOwnership: Company ownership

  Returns:
    FundamentalData with parsed fields from the XML response.

  Example:
    >>> await get_fundamental_data(symbol="AAPL", report_type="CalendarReport")
    {
      "contract_id": 265598,
      "symbol": "AAPL",
      "sec_type": "STK",
      "report_type": "CalendarReport",
      "next_earnings_date": "2025-01-15",
      "earnings_estimate": 1.45,
      "dividends": [
        {"ex_date": "2025-01-10", "pay_date": "2025-01-20", "amount": 0.24}
      ]
    }

    >>> await get_fundamental_data(contract_id=265598, report_type="ReportSnapshot")
    {
      "contract_id": 265598,
      "symbol": "AAPL",
      "report_type": "ReportSnapshot",
      "pe_ratio": 28.5,
      "dividend_yield": 0.006,
      "market_cap": 1750000000000.0,
      "sector": "Technology"
    }

  """
  if not symbol and not contract_id:
    return JSONResponse(
      status_code=400,
      content={"error": "Either 'symbol' or 'contract_id' must be provided"}
    )

  try:
    logger.debug(
      "Getting fundamental data: symbol={symbol}, contract_id={contract_id}, report_type={report_type}",
      symbol=symbol,
      contract_id=contract_id,
      report_type=report_type,
    )
    result = await ib_interface.get_fundamental_data(
      contract_id=contract_id,
      symbol=symbol,
      sec_type=sec_type,
      exchange=exchange,
      currency=currency,
      report_type=report_type,
    )
    return result
  except ValueError as e:
    logger.error("Invalid report type: {!s}", str(e))
    return JSONResponse(
      status_code=400,
      content={"error": str(e)}
    )
  except Exception as e:
    logger.error("Error in get_fundamental_data: {!s}", str(e))
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get fundamental data"}
    )
