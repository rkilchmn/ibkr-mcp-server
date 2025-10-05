"""Contract and options-related tools."""
import json
from fastapi import Query
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models import TickerData, BarData, TickData

# Module-level query parameter definitions
CONTRACT_IDS_QUERY = Query(default=None, description="List of contract IDs")
FILTERS_QUERY = Query(default=None, description="Filters as JSON string")
CRITERIA_QUERY = Query(default=None, description="Criteria as JSON string")

@ibkr_router.get(
  "/tickers",
  operation_id="get_tickers",
  response_model=list[TickerData],
)
async def get_tickers(
  contract_ids: list[int] | None = CONTRACT_IDS_QUERY,
) -> list[TickerData]:
  """Get tickers for a list of contract IDs.

  This function queries the IB TWS to get the tickers for a list of contract IDs.
  It will return the last price and symbol, and greeks (if applicable).

  Args:
    contract_ids (list[int]): A list of contract IDs to get tickers for.

  Returns:
    List[TickerData]: A list of ticker dictionaries for the contract IDs.

  Example:
    await get_tickers_details([123456, 789012])
    [
      {
        "symbol": "AAPL",
        "last": 150.75,
        "greeks": {
          "delta": 0.5,
        },
      },
      {
        "symbol": "MSFT",
        "last": 210.22,
        "greeks": null,
      },
    ]

  """
  try:
    logger.debug(
      "Getting tickers for contract IDs: {contract_ids}",
      contract_ids=contract_ids,
    )
    tickers = await ib_interface.get_tickers(contract_ids)
  except Exception as e:
    logger.error("Error in get_tickers: {!s}", str(e))
    return []
  else:
    logger.debug("Tickers: {tickers}", tickers=tickers)
    return tickers

@ibkr_router.get(
  "/filtered_options_chain",
  operation_id="get_filtered_options_chain",
  response_model=list[TickerData],
)
async def get_and_filter_options_chain(
  underlying_symbol: str,
  underlying_sec_type: str,
  underlying_con_id: int,
  filters: str | None = FILTERS_QUERY,
  criteria: str | None = CRITERIA_QUERY,
) -> list[TickerData]:
  """Get and filter option chain based on market data criteria.

  Args:
    underlying_symbol: Symbol of the underlying contract.
    underlying_sec_type: Security type of the underlying contract.
    underlying_con_id: ConID of the underlying contract.
    filters: Filters as JSON string to apply to the options chain,
    you must specify at least one filter to reduce the number of options in the chain,
    you must specify expirations, you can specify tradingClass, strikes, and rights.
      - tradingClass: List of trading classes to filter by.
      - expirations: List of expirations to filter by.
      - strikes: List of strikes to filter by.
      - rights: List of rights to filter by.
    criteria: Criteria as JSON string to filter by.
      - min_delta: Minimum delta value (float)
      - max_delta: Maximum delta value (float)

  Returns:
    list[TickerData]: A list of filtered ticker data for options.

  Example:
    await get_and_filter_options(
      underlying_symbol="SPX",
      underlying_sec_type="IND",
      underlying_con_id=416904,
      filters='{
        "tradingClass": ["SPXW"],
        "expirations": ["20250505"],
        "strikes": [5490],
        "rights": ["C", "P"],
      }',
      criteria='{"min_delta": -0.06, "max_delta": -0.04}',
    )
    [
      TickerData(symbol='SPXW 250505P05490000', last=45.50, greeks=GreeksData(delta=-0.05)), #noqa: E501
    ]

  """
  try:
    logger.debug(
      f"""
      Getting and filtering options chain for the following parameters:
      underlying_symbol: {underlying_symbol},
      underlying_sec_type: {underlying_sec_type},
      underlying_con_id: {underlying_con_id},
      filters: {filters},
      criteria: {criteria}
      """,
    )
    # Parse JSON strings to dictionaries
    filters_dict = json.loads(filters) if filters else None
    criteria_dict = json.loads(criteria) if criteria else None

    filtered_options = await ib_interface.get_and_filter_options(
      underlying_symbol,
      underlying_sec_type,
      underlying_con_id,
      filters_dict,
      criteria_dict,
    )
  except json.JSONDecodeError as e:
    logger.error("Error parsing JSON parameters: {!s}", str(e))
    return []
  except Exception as e:
    logger.error("Error in filter_options: {!s}", str(e))
    return []
  else:
    logger.debug(
      "Filtered options: {filtered_options}",
      filtered_options=filtered_options,
    )
    return filtered_options


@ibkr_router.get(
  "/market_data/historical",
  operation_id="get_historical_data",
  response_model=list[BarData],
)
async def get_historical_data(
  symbol: str = Query(..., description="Symbol to get data for"),
  sec_type: str = Query(default="STK", description="Security type"),
  exchange: str = Query(default="SMART", description="Exchange"),
  currency: str = Query(default="USD", description="Currency"),
  duration: str = Query(default="1 D", description="Duration (e.g., '1 D', '1 W', '1 M')"),
  bar_size: str = Query(default="1 min", description="Bar size (e.g., '1 min', '5 mins', '1 hour', '1 day')"),
  what_to_show: str = Query(default="TRADES", description="What to show (TRADES, MIDPOINT, BID, ASK)"),
  use_rth: bool = Query(default=True, description="Use regular trading hours only"),
) -> list[BarData]:
  """Get historical market data.
  
  Retrieve historical OHLCV bar data for a given contract.
  
  Args:
    symbol: Symbol to get data for
    sec_type: Security type (STK, OPT, FUT, etc.)
    exchange: Exchange (default: SMART)
    currency: Currency (default: USD)
    duration: Duration string (e.g., '1 D', '1 W', '1 M', '1 Y')
    bar_size: Bar size (e.g., '1 min', '5 mins', '1 hour', '1 day')
    what_to_show: What to show (TRADES, MIDPOINT, BID, ASK)
    use_rth: Use regular trading hours only
    
  Returns:
    List of historical bar data
    
  Example:
    >>> await get_historical_data(
    ...   symbol="AAPL",
    ...   sec_type="STK",
    ...   duration="1 D",
    ...   bar_size="5 mins"
    ... )
    [
      {
        "date": "2024-01-15T09:30:00",
        "open": 150.25,
        "high": 151.00,
        "low": 150.10,
        "close": 150.75,
        "volume": 125000,
        "wap": 150.50,
        "count": 450
      }
    ]
  """
  try:
    logger.debug(f"Getting historical data for {symbol}")
    bars = await ib_interface.get_historical_data(
      symbol=symbol,
      sec_type=sec_type,
      exchange=exchange,
      currency=currency,
      duration=duration,
      bar_size=bar_size,
      what_to_show=what_to_show,
      use_rth=use_rth
    )
    return bars
  except Exception as e:
    logger.error(f"Error in get_historical_data: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get historical data"}
    )


@ibkr_router.get(
  "/market_data/snapshot",
  operation_id="get_market_data_snapshot",
  response_model=TickData | None,
)
async def get_market_data_snapshot(
  symbol: str = Query(..., description="Symbol to get data for"),
  sec_type: str = Query(default="STK", description="Security type"),
  exchange: str = Query(default="SMART", description="Exchange"),
  currency: str = Query(default="USD", description="Currency"),
  con_id: int | None = Query(default=None, description="Contract ID (optional)"),
) -> TickData | None:
  """Get real-time market data snapshot.
  
  Retrieve current market data including last price, bid, ask, and sizes.
  
  Args:
    symbol: Symbol to get data for
    sec_type: Security type (STK, OPT, FUT, etc.)
    exchange: Exchange (default: SMART)
    currency: Currency (default: USD)
    con_id: Contract ID (optional, for direct lookup)
    
  Returns:
    Tick data with current market information or None if not available
    
  Example:
    >>> await get_market_data_snapshot(symbol="AAPL", sec_type="STK")
    {
      "symbol": "AAPL",
      "contract_id": 265598,
      "last": 155.50,
      "bid": 155.48,
      "ask": 155.52,
      "bid_size": 100,
      "ask_size": 200,
      "volume": 1250000,
      "timestamp": "2024-01-15T10:30:00"
    }
  """
  try:
    logger.debug(f"Getting market data snapshot for {symbol}")
    tick_data = await ib_interface.get_market_data_snapshot(
      symbol=symbol,
      sec_type=sec_type,
      exchange=exchange,
      currency=currency,
      con_id=con_id
    )
    return tick_data
  except Exception as e:
    logger.error(f"Error in get_market_data_snapshot: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get market data snapshot"}
    )
