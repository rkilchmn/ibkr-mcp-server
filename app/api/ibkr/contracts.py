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
) -> dict:
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
    dict: A JSON response containing either:
      - {"qualified_contract": {...}} when a single matching contract is found
      - {"candidate_contracts": [...]} when multiple contract candidates are found
      - {"error": "..."} when an error occurs

  Example:
    >>> get_contract_details(symbol="AAPL", sec_type="STK", exchange="NASDAQ")
    {"qualified_contract": {"symbol": "AAPL", "sec_type": "STK", "exchange": "NASDAQ"}}

  """
  try:
    logger.debug("Getting contract details for symbol: {symbol}", symbol=symbol)
    options_dict = json.loads(options) if options else {}
    result = await ib_interface.get_contract_details(
      symbol=symbol,
      sec_type=sec_type,
      exchange=exchange,
      primary_exchange=primary_exchange,
      currency=currency,
      options=options_dict,
    )
  except Exception as e:
    logger.error("Error in get_contract_details: {!s}", str(e))
    return {"error": "Error getting contract details"}
  else:
    if isinstance(result, list):
      logger.debug("Candidate contracts found: {candidate_contracts}", candidate_contracts=result)
      return {"candidate_contracts": result}
    else:
      logger.debug("Qualified contract found: {qualified_contract}", qualified_contract=result)
      return {"qualified_contract": result}

@ibkr_router.get("/options_chain", operation_id="get_options_chain")
async def get_options_chain(
  underlying_symbol: str,
  underlying_sec_type: str,
  underlying_con_id: int,
  exchange: str | None = None,
  filters: str | None = FILTERS_QUERY,
) -> dict:
  """Get options chain for a given underlying contract.

  Args:
    underlying_symbol (str): Symbol of the underlying contract.
    underlying_sec_type (str): Security type of the underlying contract.
    underlying_con_id (int): ConID of the underlying contract.
    exchange (str | None): Exchange to filter chains by (e.g., SMART, CBOE).
      If not specified and multiple chains are available, returns candidate chains.
    filters (str | None): filters as JSON string to apply to the options chain,
      you must specify at least one filter to reduce the number of options in the chain,
      you must specify expirations, you can specify tradingClass, strikes, and rights.
      - tradingClass: List of trading classes to filter by.
      - expirations: List of expirations to filter by.
      - strikes: List of strikes to filter by.
      - rights: List of rights to filter by.

  Returns:
    dict: A JSON response containing either:
      - {"options_chain": [...]} when a single chain is found/selected
      - {"candidate_chains": [...]} when multiple chain candidates are found
      - {"error": "..."} when an error occurs

  Example:
    >>> get_options_chain(
      underlying_symbol="CCJ",
      underlying_sec_type="STK",
      underlying_con_id=1447060,
      exchange="SMART",
      filters='{
        "tradingClass": ["CCJ"],
        "expirations": ["20270206"],
        "rights": ["C"],
        "strikes": [120],
      }',
    )
    {"options_chain": [
      {"con_id":123456789,"symbol":"CCJ","sec_type":"OPT","last_trade_date_or_contract_month":"20270206","strike":120.0,"right":"C"}
    ]}

  """
  try:
    logger.debug("Getting options chain for symbol: {symbol}", symbol=underlying_symbol)
    filters_dict = json.loads(filters) if filters else {}
    result = await ib_interface.get_options_chain(
      underlying_symbol=underlying_symbol,
      underlying_sec_type=underlying_sec_type,
      underlying_con_id=underlying_con_id,
      exchange=exchange,
      filters=filters_dict,
    )
  except Exception as e:
    logger.error("Error in get_options_chain: {!s}", str(e))
    return {"error": "Error getting options chain"}
  else:
    if isinstance(result, list) and result and "expirations" in result[0]:
      # It's a list of candidate chains
      logger.debug("Candidate chains found: {candidate_chains}", candidate_chains=result)
      return {"candidate_chains": result}
    else:
      # It's an options chain
      logger.debug("Options chain found: {options_chain}", options_chain=result)
      return {"options_chain": result}
