"""Contract and options-related tools."""
from loguru import logger
from app.api.endpoints.ibkr import ibkr_router, ib_interface

@ibkr_router.post("/contract_details")
async def get_contract_details(
  symbol: str,
  sec_type: str,
  exchange: str,
  options: dict | None = None,
) -> str:
  """Get contract details for a given symbol.

  Args:
    symbol (str): Symbol to get contract details for.
    sec_type (str): Security type (STK, IND, CASH, BAG, BOND, FUT, OPT)
    exchange (str): Exchange (CBOE, NYSE, ARCA, BATS, NASDAQ)
    options (dict | None): Optional parameters including:
      - lastTradeDateOrContractMonth: Expiry date for options - "YYYYMMDD"
      - strike: Strike price for options
      - right: Right for options - "C" or "P"
      - tradingClass: for weekly options of SPX use SPXW

  Returns:
    str: A formatted string containing the contract details or error message

  Example:
    get_contract_details(symbol="AAPL", sec_type="STK", exchange="NASDAQ")

    "The contract details for the symbol are:
      {'symbol': 'AAPL',
      'secType': 'STK',
      'exchange': 'NASDAQ'}"

  """
  try:
    options = options or {}
    details = await ib_interface.get_contract_details(
      symbol=symbol,
      sec_type=sec_type,
      exchange=exchange,
      options=options,
    )
  except Exception as e:
    logger.error("Error in get_contract_details: {!s}", str(e))
    return "Error getting contract details"
  else:
    return f"The contract details for the symbol are: {details}"

@ibkr_router.post("/options_chain")
async def get_options_chain(
  underlying_symbol: str,
  underlying_sec_type: str,
  underlying_con_id: int,
  filters: dict | None = None,
) -> str:
  """Get options chain for a given underlying contract.

  Args:
    underlying_symbol: Symbol of the underlying contract.
    underlying_sec_type: Security type of the underlying contract.
    underlying_con_id: ConID of the underlying contract.
    filters: Dictionary of filters to apply to the options chain,
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
    ...     underlying_symbol="SPX",
    ...     underlying_sec_type="IND",
    ...     underlying_con_id=416904,
    ...     filters={
    ...       "tradingClass": ["SPXW"],
    ...       "expirations": ["20250505"],
    ...       "strikes": [5490],
    ...       "rights": ["C", "P"],
    ...     },
    ... )
    "The options chain for the underlying contract is: [
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
    options_chain = await ib_interface.get_options_chain(
      underlying_symbol,
      underlying_sec_type,
      underlying_con_id,
      filters,
    )
  except Exception as e:
    logger.error("Error in get_options_chain: {!s}", str(e))
    return "Error getting options chain"
  else:
    return f"The options chain for the underlying contract is: {options_chain}"
