"""Gateway endpoints."""

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel

from app.core.accounts import UnknownAccountError, get_account_registry
from app.core.setup_logging import logger
from app.gateway.gateway_manager import IBKRGatewayManager

router = APIRouter(prefix="/gateway", tags=["gateway"])

# Global gateway manager instance
gateway_manager = IBKRGatewayManager()

ACCOUNT_ID_QUERY = Query(
  default=None,
  description="Account to use (account id from /gateway/status). Empty/omitted uses the default account.", #noqa: E501
)


class IBKRConnectionRequest(BaseModel):
  """Request body for connecting to IBKR."""
  account_id: str | None = None
  username: str | None = None


class GatewayConnectResponse(BaseModel):
  """Response for gateway connect."""
  success: bool
  message: str
  account_id: str | None = None
  username: str | None = None


@router.get("/status", operation_id="get_ibkr_gateway_status")
async def get_gateway_status() -> dict:
  """Get the current status of all IBKR Gateways.

  One container per configured account runs in parallel on dedicated ports.

  Returns:
    dict: A dictionary containing the list of available accounts. Only
      account_id and description are exposed per account (usernames stay
      private), plus each account's remote desktop port (VNC for ib-gateway
      images, RDP for tws-rdesktop images) and its container status.

  Example:
    >>> get_gateway_status()
    {
      "accounts": [
        {
          "account_id": "DUP420996",
          "description": "Roger SG - Paper Trading",
          "is_running": true,
          "vnc_port": 5901,
          "rdp_port": null,
          "container": {
            "status": "running",
            "health": "healthy",
            "created": "2025-06-29T02:09:51.071992384Z",
            "started": "2025-06-29T02:09:51.287050095Z",
            "finished": "0001-01-01T00:00:00Z",
            "age": 82410.913484
          }
        }
      ]
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
async def get_gateway_logs(
  tail: int = 100,
  account_id: str | None = ACCOUNT_ID_QUERY,
) -> dict:
  """Get the logs from an IBKR Gateway container.

  Args:
    tail (int): The number of lines to return from the end of the logs.
    account_id (str | None): Account to use (account id from /gateway/status).
      Empty/omitted uses the default account.

  Returns:
    dict: A dictionary containing the logs from the IBKR Gateway container.

  Example:
    >>> get_gateway_logs(tail=5)
    {
      "logs": [
        "remove Client 1111",
        "2025/06/30 01:03:22 socat[1281] N socket 1 (fd 6) is at EOF",
        "2025/06/30 01:03:22 socat[1281] N socket 2 (fd 5) is at EOF"
      ]
    }

  """
  try:
    return await gateway_manager.get_gateway_logs(tail, account_id)
  except UnknownAccountError as e:
    raise HTTPException(status_code=404, detail=str(e)) from e
  except Exception as err:
    logger.exception("Error getting gateway logs.")
    raise HTTPException(
      status_code=500,
      detail="Failed to get gateway logs.",
    ) from err


@router.post("/connect", operation_id="connect_ibkr_gateway", response_model=GatewayConnectResponse)
async def connect_gateway(request: IBKRConnectionRequest = Body(...)) -> GatewayConnectResponse:
  """Connect to an IBKR Gateway account.

  Starts (or restarts, when the username differs from the configured one) the
  gateway container for the requested account. Each account runs in its own
  container on dedicated ports.

  Args:
    request: Connection request with an optional account_id and/or legacy
      username. account_id takes precedence. If both are empty, connects the
      default account.

  Returns:
    GatewayConnectResponse with success status, message and account id

  """
  try:
    if request.account_id:
      logger.info(f"Connecting to IBKR Gateway for account: {request.account_id}")
      success = await gateway_manager.start_gateway(request.account_id)
      if success:
        account = get_account_registry().get(request.account_id)
        return GatewayConnectResponse(
          success=True,
          message=f"Successfully connected to IBKR Gateway for account {account.account_id}",
          account_id=account.account_id,
        )
    elif request.username:
      logger.info(f"Connecting to IBKR Gateway with username: {request.username}")
      success = await gateway_manager.restart_gateway_with_user(request.username)
      if success:
        account = get_account_registry().get_by_username(request.username)
        return GatewayConnectResponse(
          success=True,
          message=f"Successfully connected to IBKR Gateway",
          account_id=account.account_id if account else None,
          username=request.username,
        )
    else:
      logger.info("Connecting to IBKR Gateway with default account")
      success = await gateway_manager.start_gateway()
      if success:
        account = get_account_registry().default_account
        return GatewayConnectResponse(
          success=True,
          message=f"Successfully connected to IBKR Gateway for default account {account.account_id}",
          account_id=account.account_id,
        )

    # Distinguish unknown account from startup failure
    try:
      get_account_registry().get(request.account_id)
      detail = "Failed to connect to IBKR Gateway"
    except UnknownAccountError as e:
      detail = str(e)

    return GatewayConnectResponse(
      success=False,
      message=detail,
      account_id=request.account_id,
      username=request.username,
    )
  except Exception as e:
    logger.exception("Error connecting to IBKR Gateway")
    return GatewayConnectResponse(
      success=False,
      message=f"Connection error: {str(e)}",
      account_id=request.account_id,
      username=request.username,
    )
