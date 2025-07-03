"""Scanner-related tools."""
from fastapi import Query
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger

# Module-level query parameter definitions
FILTER_CODES_QUERY = Query(
  default=None,
  description="List of filter parameters in 'parameter=value' format",
)

@ibkr_router.get(
  "/scanner/instrument_codes",
  operation_id="get_scanner_instrument_codes",
)
async def get_scanner_instrument_codes() -> str:
  """Get scanner instrument codes from Interactive Brokers TWS.

  This function queries the IB TWS scanner to find the instrument codes.

  Returns:
    str: A formatted string containing the scanner instrument codes or error message

  Example:
    >>> get_scanner_instrument_codes()
    "The scanner instrument codes are: ['STK', 'FUT', 'OPT']"

  """
  try:
    logger.debug("Getting scanner instrument codes")
    tags = await ib_interface.get_scanner_instrument_codes()
  except Exception as e:
    logger.error("Error in get_scanner_instrument_codes: {!s}", str(e))
    return "Error getting scanner instrument codes"
  else:
    logger.debug("Scanner instrument codes: {tags}", tags=tags)
    return f"The scanner instrument codes are: {tags}"

@ibkr_router.get("/scanner/location_codes", operation_id="get_scanner_location_codes")
async def get_scanner_location_codes() -> str:
  """Get scanner location codes from Interactive Brokers TWS.

  This function queries the IB TWS scanner to find the location codes.

  Returns:
    str: A formatted string containing the scanner location codes or error message

  Example:
    >>> get_scanner_location_codes()
    "The scanner location codes are: ['STK.US', 'STK.EU']"

  """
  try:
    logger.debug("Getting scanner location codes")
    tags = await ib_interface.get_scanner_location_codes()
  except Exception as e:
    logger.error("Error in get_scanner_location_codes: {!s}", str(e))
    return "Error getting scanner location codes"
  else:
    logger.debug("Scanner location codes: {tags}", tags=tags)
    return f"The scanner location codes are: {tags}"

@ibkr_router.get("/scanner/filter_codes", operation_id="get_scanner_filter_codes")
async def get_scanner_filter_codes() -> str:
  """Get scanner filter codes from Interactive Brokers TWS.

  This function queries the IB TWS scanner to find the filter codes.

  Returns:
    str: A formatted string containing the scanner filter codes or error message

  Example:
    >>> get_scanner_filter_codes()
    "The scanner filter codes are: ['priceAbove', 'marketCapAbove']"

  """
  try:
    logger.debug("Getting scanner filter codes")
    tags = await ib_interface.get_scanner_filter_codes()
  except Exception as e:
    logger.error("Error in get_scanner_filter_codes: {!s}", str(e))
    return "Error getting scanner filter codes"
  else:
    logger.debug("Scanner filter codes: {tags}", tags=tags)
    return f"The scanner filter codes are: {tags}"

@ibkr_router.get("/scanner/results", operation_id="get_scanner_results")
async def get_scanner_results(
  instrument_code: str,
  location_code: str,
  filter_codes: list[str] | None = FILTER_CODES_QUERY,
) -> str:
  """Get scanner results from Interactive Brokers TWS.

  This function queries the IB TWS scanner with specified parameters to find
  instruments matching the given criteria.

  Args:
    instrument_code (str): Type of instrument to scan for (e.g., 'STK', 'FUT', 'OPT')
    location_code (str): Geographic location/market code (e.g., 'STK.US', 'STK.EU')
    filter_codes (list[str]): List of filter parameters in 'parameter=value' format,
      e.g. ['priceAbove=10', 'marketCapAbove=1000000000']

  Returns:
    str: A formatted string containing the scanner results or error message

  Example:
    >>> get_scanner_results(
      instrument_code="STK",
      location_code="STK.US",
      filter_codes=["priceAbove=10", "marketCapAbove=1000000000"],
    )
    "I found 2 stocks matching the scanner parameters: ['AAPL', 'GOOG']"

  """
  try:
    logger.debug(
      f"""
      Getting scanner results for instrument code: {instrument_code},
      location code: {location_code},
      filter codes: {filter_codes}
      """,
    )
    results = await ib_interface.get_scanner_results(
      instrument_code,
      location_code,
      filter_codes or [],
    )
  except Exception as e:
    logger.error("Error in get_scanner_results: {!s}", str(e))
    return "Error getting scanner results"
  else:
    logger.debug("Scanner results: {results}", results=results)
    return f"I found {len(results)} stocks matching the scanner parameters: {results}"
