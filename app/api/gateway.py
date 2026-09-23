"""Gateway endpoints."""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from app.core.setup_logging import logger
from app.gateway.gateway_manager import IBKRGatewayManager

router = APIRouter(prefix="/gateway", tags=["gateway"])

# Global gateway manager instance
gateway_manager = IBKRGatewayManager()


class IBKRConnectionRequest(BaseModel):
  """Request body for connecting to IBKR."""
  username: str | None = None


class GatewayConnectResponse(BaseModel):
  """Response for gateway connect."""
  success: bool
  message: str
  username: str | None = None

@router.get("/status", operation_id="get_ibkr_gateway_status")
async def get_gateway_status() -> dict:
  """Get the current status of the IBKR Gateway.

  Returns:
    dict: A dictionary containing the status of the IBKR Gateway.

  Example:
    >>> get_gateway_status()
  {
    "is_running": true,
    "username": "d3f93tn6z",
    "image": "ghcr.io/gnzsnz/tws-rdesktop:latest",
    "container": {
      "status": "running",
      "health": "healthy",
      "created": "2025-06-29T02:09:51.071992384Z",
      "started": "2025-06-29T02:09:51.287050095Z",
      "finished": "0001-01-01T00:00:00Z",
      "age": 82410.913484
    }
  }

  """
  try:
    return await gateway_manager.get_gateway_status()
  except Exception as err:
    logger.exception("Error getting gateway status.")
    raise HTTPException(
      status_code=500,
      detail="Failed to get gateway status.",
    ) from err


@router.get("/logs", operation_id="get_ibkr_gateway_logs")
async def get_gateway_logs(tail: int = 100) -> dict:
  """Get the logs from the IBKR Gateway container.

  Args:
    tail (int): The number of lines to return from the end of the logs.

  Returns:
    dict: A dictionary containing the logs from the IBKR Gateway container.

  Example:
    >>> get_gateway_logs(tail=5)
    {
      "logs": [
        "remove Client 1111",
        "2025/06/30 01:03:22 socat[1281] N socket 1 (fd 6) is at EOF",
        "2025/06/30 01:03:22 socat[1281] N socket 2 (fd 5) is at EOF",
        "2025/06/30 01:03:22 socat[11] N exiting with status 0",
        "2025/06/30 01:03:22 socat[11] N childdied(): handling signal 17"
      ]
    }

  """
  try:
    return await gateway_manager.get_gateway_logs(tail)
  except Exception as err:
    logger.exception("Error getting gateway logs.")
    raise HTTPException(
      status_code=500,
      detail="Failed to get gateway logs.",
    ) from err


@router.post("/connect", operation_id="connect_ibkr_gateway", response_model=GatewayConnectResponse)
async def connect_gateway(request: IBKRConnectionRequest) -> GatewayConnectResponse:
  """Connect to IBKR Gateway with optional username.

  If username is provided and differs from current, restarts the gateway container
  with the new username (different docker compose). If empty, uses the configured
  username from env/.env.

  Args:
    request: Connection request with optional username

  Returns:
    GatewayConnectResponse with success status and message

  """
  try:
    username = request.username
    if username:
      logger.info(f"Connecting to IBKR Gateway with username: {username}")
      success = await gateway_manager.restart_gateway_with_user(username)
    else:
      logger.info("Connecting to IBKR Gateway with default username")
      success = await gateway_manager.start_gateway()

    if success:
      return GatewayConnectResponse(
        success=True,
        message="Successfully connected to IBKR Gateway",
        username=username,
      )
    else:
      return GatewayConnectResponse(
        success=False,
        message="Failed to connect to IBKR Gateway",
        username=username,
      )
  except Exception as e:
    logger.exception("Error connecting to IBKR Gateway")
    return GatewayConnectResponse(
      success=False,
      message=f"Connection error: {str(e)}",
      username=request.username,
    )
