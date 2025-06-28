from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from app.gateway.gateway_manager import IBKRGatewayManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gateway", tags=["gateway"])

# Global gateway manager instance
gateway_manager = IBKRGatewayManager()


class IBKRConnectionRequest(BaseModel):
  host: str = "127.0.0.1"
  port: int = 4001
  client_id: int = 1


@router.get("/status")
async def get_gateway_status():
  """Get the current status of the IBKR Gateway."""
  try:
    status = await gateway_manager.get_gateway_status()
    return status
  except Exception as e:
    logger.error(f"Error getting gateway status: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_gateway_logs(tail: int = 100):
  """Get the logs from the IBKR Gateway container."""
  try:
    logs = await gateway_manager.get_gateway_logs(tail)
    return {"logs": logs}
  except Exception as e:
    logger.error(f"Error getting gateway logs: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect")
async def connect_to_ibkr(request: IBKRConnectionRequest):
  """Connect to IBKR TWS/Gateway through the container."""
  try:
    success = await gateway_manager.connect_to_ibkr(
      host=request.host,
      port=request.port,
      client_id=request.client_id
    )

    if success:
      return {"message": "Connected to IBKR successfully", "status": "connected"}
    else:
      raise HTTPException(status_code=500, detail="Failed to connect to IBKR")
  except Exception as e:
    logger.error(f"Error connecting to IBKR: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_from_ibkr():
  """Disconnect from IBKR TWS/Gateway."""
  try:
    success = await gateway_manager.disconnect_from_ibkr()

    if success:
      return {"message": "Disconnected from IBKR successfully", "status": "disconnected"}
    else:
      raise HTTPException(status_code=500, detail="Failed to disconnect from IBKR")
  except Exception as e:
    logger.error(f"Error disconnecting from IBKR: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/account")
async def get_account_info():
  """Get account information from IBKR."""
  try:
    account_info = await gateway_manager.get_account_info()
    return account_info
  except Exception as e:
    logger.error(f"Error getting account info: {e}")
    raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio")
async def get_portfolio():
  """Get portfolio positions from IBKR."""
  try:
    portfolio = await gateway_manager.get_portfolio()
    return {"positions": portfolio}
  except Exception as e:
    logger.error(f"Error getting portfolio: {e}")
    raise HTTPException(status_code=500, detail=str(e))
