"""Contract and options-related tools."""

import json
from fastapi import Query
from loguru import logger
from app.api.ibkr import ibkr_router, ib_interface

# Module-level query parameter definitions
OPTIONS_QUERY = Query(default=None, description="Optional parameters as JSON string")
FILTERS_QUERY = Query(default=None, description="Filters as JSON string")

@ibkr_router.get("/contract_details", operation_id="get_contract_details")
async def get_contract_details(
  symbol: str,
  sec_type: str,
  exchange: str | None = None,
  primary_exchange: str | None = None,
  currency: str | None = None,
  options: str | None = OPTIONS_QUERY,
) -> str:
  """Get contract details for a given symbol.

  Args:
    symbol (str): Symbol to get contract details for.
    sec_type (str): Security type (STK, IND, CASH, BAG, BOND, FUT, OPT)
    exchange (str): Exchange (CBOE, NYSE, ARCA, BATS, NASDAQ)
    primary_exchange (str | None): Primary exchange for the contract
    options (str | None): Optional parameters as JSON string including:
      - lastTradeDateOrContractMonth: Expiry date for options - "YYYYMMDD"
      - strike: Strike price for options
      - right: Right for options - "C" or "P"
      - tradingClass: for weekly options of SPX use SPXW

  Returns:
    str: A formatted string containing the contract details or error message

  Example:
    >>> get_contract_details(symbol="AAPL", sec_type="STK", exchange="NASDAQ")
    "The contract details for the symbol are:
      {'symbol': 'AAPL',
      'secType': 'STK',
      'exchange': 'NASDAQ'}"

  """
  try:
    logger.debug("Getting contract details for symbol: {symbol}", symbol=symbol)
    options_dict = json.loads(options) if options else {}
    details = await ib_interface.get_contract_details(
      symbol=symbol,
      sec_type=sec_type,
      exchange=exchange,
      primary_exchange=primary_exchange,
      currency=currency,
      options=options_dict,
    )
  except Exception as e:
    logger.error("Error in get_contract_details: {!s}", str(e))
    return "Error getting contract details"
  else:
    logger.debug("Contract details: {details}", details=details)
    return f"{details}"

@ibkr_router.get("/options_chain", operation_id="get_options_chain")
async def get_options_chain(
  underlying_symbol: str,
  underlying_sec_type: str,
  underlying_con_id: int,
  filters: str | None = FILTERS_QUERY,
) -> str:
  """Get options chain for a given underlying contract.

  Args:
    underlying_symbol (str): Symbol of the underlying contract.
    underlying_sec_type (str): Security type of the underlying contract.
    underlying_con_id (int): ConID of the underlying contract.
    filters (str | None): filters as JSON string to apply to the options chain,
      you must specify at least one filter to reduce the number of options in the chain,
      you must specify expirations, you can specify tradingClass, strikes, and rights.
      - tradingClass: List of trading classes to filter by.
      - expirations: List of expirations to filter by.
      - strikes: List of strikes to filter by.
      - rights: List of rights to filter by.

  Returns:
    str: A formatted string containing the options chain or error message

  Example:
    >>> get_options_chain(
      underlying_symbol="SPX",
      underlying_sec_type="IND",
      underlying_con_id=416904,
      filters='{
        "tradingClass": ["SPXW"],
        "expirations": ["20250505"],
        "rights": ["C", "P"],
        "strikes": [5490],
      }',
    )
    "[
      [
      {"conId":771890640,"localSymbol":"SPXW  250505P06200000"},
      {"conId":771890645,"localSymbol":"SPXW  250505P06400000"},
      {"conId":771890655,"localSymbol":"SPXW  250505P06600000"},
      {"conId":771890665,"localSymbol":"SPXW  250505P06800000"},
      {"conId":771890685,"localSymbol":"SPXW  250505P07000000"},
      {"conId":771890699,"localSymbol":"SPXW  250505P07200000"},
      {"conId":771890709,"localSymbol":"SPXW  250505P07400000"},
    ]"

  """
  try:
    logger.debug("Getting options chain for symbol: {symbol}", symbol=underlying_symbol)
    filters_dict = json.loads(filters) if filters else {}
    options_chain = await ib_interface.get_options_chain(
      underlying_symbol,
      underlying_sec_type,
      underlying_con_id,
      filters_dict,
    )
  except Exception as e:
    logger.error("Error in get_options_chain: {!s}", str(e))
    return "Error getting options chain"
  else:
    logger.debug("Options chain: {options_chain}", options_chain=options_chain)
    return f"The available options contracts are: {options_chain}"
