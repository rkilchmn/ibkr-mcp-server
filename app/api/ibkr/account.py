"""Account management endpoints."""
from fastapi import Query
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models import AccountSummary, AccountValue, Position


@ibkr_router.get(
  "/account/summary",
  operation_id="get_account_summary",
  response_model=list[AccountSummary],
)
async def get_account_summary(
  tags: str = Query(default="All", description="Tags to retrieve (default: All)")
) -> list[AccountSummary]:
  """Get account summary information.
  
  Returns account summary data including balances, buying power, and other account metrics.
  
  Args:
    tags: Comma-separated list of tags to retrieve. Use "All" for all available tags.
    
  Returns:
    List of account summary items with tag, value, currency, and account information.
    
  Example:
    >>> await get_account_summary(tags="NetLiquidation,TotalCashValue")
    [
      {"account": "DU123456", "tag": "NetLiquidation", "value": "100000.00", "currency": "USD"},
      {"account": "DU123456", "tag": "TotalCashValue", "value": "50000.00", "currency": "USD"}
    ]
  """
  try:
    logger.debug(f"Getting account summary with tags: {tags}")
    summary = await ib_interface.get_account_summary(tags)
    return summary
  except Exception as e:
    logger.error(f"Error in get_account_summary: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get account summary"}
    )


@ibkr_router.get(
  "/account/values",
  operation_id="get_account_values",
  response_model=list[AccountValue],
)
async def get_account_values() -> list[AccountValue]:
  """Get all account values.
  
  Returns detailed account value information including all available account metrics.
  
  Returns:
    List of account values with key, value, currency, and account information.
    
  Example:
    >>> await get_account_values()
    [
      {"account": "DU123456", "key": "CashBalance", "value": "50000.00", "currency": "USD"},
      {"account": "DU123456", "key": "StockMarketValue", "value": "50000.00", "currency": "USD"}
    ]
  """
  try:
    logger.debug("Getting account values")
    values = await ib_interface.get_account_values()
    return values
  except Exception as e:
    logger.error(f"Error in get_account_values: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get account values"}
    )


@ibkr_router.get(
  "/account/positions",
  operation_id="get_positions_detailed",
  response_model=list[Position],
)
async def get_positions_detailed() -> list[Position]:
  """Get detailed position information.
  
  Returns all positions with market data, P&L, and contract details.
  
  Returns:
    List of positions with symbol, quantity, average cost, market value, and P&L.
    
  Example:
    >>> await get_positions_detailed()
    [
      {
        "account": "DU123456",
        "symbol": "AAPL",
        "sec_type": "STK",
        "exchange": "NASDAQ",
        "currency": "USD",
        "position": 100.0,
        "avg_cost": 150.25,
        "market_price": 155.50,
        "market_value": 15550.00,
        "unrealized_pnl": 525.00,
        "realized_pnl": null,
        "contract_id": 265598
      }
    ]
  """
  try:
    logger.debug("Getting detailed positions")
    positions = await ib_interface.get_positions_detailed()
    return positions
  except Exception as e:
    logger.error(f"Error in get_positions_detailed: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get detailed positions"}
    )
