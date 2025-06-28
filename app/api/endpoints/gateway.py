"""Gateway endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.setup_logging import logger
from app.gateway.gateway_manager import IBKRGatewayManager

router = APIRouter(prefix="/gateway", tags=["gateway"])

# Global gateway manager instance
gateway_manager = IBKRGatewayManager()


class IBKRConnectionRequest(BaseModel):
  """Request body for connecting to IBKR."""

@router.get("/status")
async def get_gateway_status() -> dict:
  """Get the current status of the IBKR Gateway."""
  try:
    return await gateway_manager.get_gateway_status()
  except Exception as err:
    logger.exception("Error getting gateway status.")
    raise HTTPException(
      status_code=500,
      detail="Failed to get gateway status.",
    ) from err


@router.get("/logs")
async def get_gateway_logs(tail: int = 100) -> dict:
  """Get the logs from the IBKR Gateway container."""
  try:
    return await gateway_manager.get_gateway_logs(tail)
  except Exception as err:
    logger.exception("Error getting gateway logs.")
    raise HTTPException(
      status_code=500,
      detail="Failed to get gateway logs.",
    ) from err
