"""Position-related tools."""
from fastapi import Query
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, resolve_interface
from app.core.setup_logging import logger

@ibkr_router.get("/positions", operation_id="get_positions")
async def get_positions(
  account_id: str | None = Query(default=None, description="Account to use (account id from /gateway/status). Empty/omitted uses the default account."), #noqa: E501
) -> list[dict]:
  """Get positions for all accounts.

  Args:
    account_id: Account to use (account id from /gateway/status).
      Empty/omitted uses the default account.

  Returns:
    list[dict]: A list of dictionaries containing the positions for the accounts.

  Example:
    [
      {
        "account": "DU123456",
        "symbol": "AAPL",
        "position": 100.0,
        "avg_cost": 150.25,
        "contract_id": 123456
      }
    ]

  """
  iface = resolve_interface(account_id)
  try:
    logger.debug("Getting positions")
    positions = await iface.get_positions()
  except Exception as e:
    logger.error("Error in get_positions: {!s}", str(e))
    return JSONResponse(content=[], media_type="application/json")
  else:
    logger.debug("Positions: {positions}", positions=positions)
    return JSONResponse(content=positions, media_type="application/json")
