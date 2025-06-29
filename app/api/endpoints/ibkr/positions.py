"""Position-related tools."""
from app.api.endpoints.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger

@ibkr_router.get("/positions")
async def get_positions() -> list[dict]:
  """Get positions for all accounts.

  Returns:
    list[dict]: A list of dictionaries containing the positions for the accounts.

  Example:
    >>> await get_positions()
    [{"contract":"AAPL","position":100,"avgCost":150.25,"contractId":123456}]

  """
  try:
    positions = await ib_interface.get_positions()
    logger.debug("Positions: {}", positions)
  except Exception as e:
    logger.error("Error in get_positions: {!s}", str(e))
    return []
  else:
    return positions
