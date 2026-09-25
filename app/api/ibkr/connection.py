"""Connection management endpoints."""
from fastapi import Query
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, resolve_interface
from app.core.accounts import get_account_registry, remote_desktop_access
from app.core.setup_logging import logger
from app.models import ConnectionStatus, ReconnectResponse

ACCOUNT_ID_QUERY = Query(
  default=None,
  description="Account to use (account id from /gateway/status). Empty/omitted uses the default account.", #noqa: E501
)


def _annotate_with_access_ports(status: ConnectionStatus) -> None:
  """Add the account's VNC/RDP port (depending on image type) to a status."""
  account = get_account_registry().get(status.account_id)
  access_type, _access_port = remote_desktop_access(account)
  if access_type == "rdp":
    status.rdp_port = account.rdp_port
  else:
    status.vnc_port = account.vnc_port


@ibkr_router.get(
  "/connection/status",
  operation_id="get_connection_status",
  response_model=ConnectionStatus,
)
async def get_connection_status(
  account_id: str | None = ACCOUNT_ID_QUERY,
) -> ConnectionStatus:
  """Get current connection status.

  Check the status of the connection to IBKR Gateway/TWS for an account.

  Args:
    account_id: Account to use (account id from /gateway/status).
      Empty/omitted uses the default account.

  Returns:
    Connection status including host, port, connected state, and accounts.
    Also includes the account's remote desktop port (VNC for ib-gateway
    images, RDP for tws-rdesktop images).

  Example:
    {
      "connected": true,
      "host": "localhost",
      "port": 4002,
      "client_id": null,
      "accounts": ["DU123456"],
      "account_id": "DUP420996",
      "vnc_port": 5901,
      "rdp_port": null
    }

  """
  iface = resolve_interface(account_id)
  try:
    logger.debug(f"Getting connection status for account_id={account_id}")
    status = await iface.get_connection_status()
    if account_id and str(account_id).strip():
      status.account_id = str(account_id).strip()
    else:
      status.account_id = get_account_registry().default_account.account_id
    _annotate_with_access_ports(status)
    return status
  except Exception as e:
    logger.error(f"Error in get_connection_status: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to get connection status"}
    )


@ibkr_router.post(
  "/connection/reconnect",
  operation_id="reconnect",
  response_model=ReconnectResponse,
)
async def reconnect(account_id: str | None = ACCOUNT_ID_QUERY) -> ReconnectResponse:
  """Reconnect to IBKR Gateway/TWS.

  Disconnect and reconnect to the IBKR Gateway/TWS of an account. Useful when
  connection is lost or needs to be refreshed.

  Args:
    account_id: Account to use (account id from /gateway/status).
      Empty/omitted uses the default account.

  Returns:
    Reconnection response with success status and message

  Example:
    >>> await reconnect()
    {
      "success": true,
      "message": "Successfully reconnected to IBKR Gateway",
      "connected": true
    }
  """
  iface = resolve_interface(account_id)
  try:
    logger.debug(f"Attempting to reconnect (account_id={account_id})")
    response = await iface.reconnect()
    return response
  except Exception as e:
    logger.error(f"Error in reconnect: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to reconnect"}
    )
