"""Position-related tools."""
from fastapi.responses import JSONResponse
from app.api.endpoints.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger

@ibkr_router.get(
  "/positions",
  operation_id="ibkr_get_positions",
)
async def get_positions() -> list[dict]:
  """Get positions for all accounts.

  Returns:
    list[dict]: A list of dictionaries containing the positions for the accounts.

  Example:
    >>> get_positions()
    [0:{"contract":"AAPL","position":100,"avgCost":150.25,"contractId":123456}]

  """
  try:
    positions = await ib_interface.get_positions()
  except Exception as e:
    logger.error("Error in get_positions: {!s}", str(e))
    return JSONResponse(content=[], media_type="application/json")
  else:
    return JSONResponse(content=positions, media_type="application/json")
