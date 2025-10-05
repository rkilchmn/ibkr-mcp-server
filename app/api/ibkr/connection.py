"""Connection management endpoints."""
from fastapi.responses import JSONResponse
from app.api.ibkr import ibkr_router, ib_interface
from app.core.setup_logging import logger
from app.models import ConnectionStatus, ReconnectResponse


@ibkr_router.get(
  "/connection/status",
  operation_id="get_connection_status",
  response_model=ConnectionStatus,
)
async def get_connection_status() -> ConnectionStatus:
  """Get current connection status.
  
  Check the status of the connection to IBKR Gateway/TWS.
  
  Returns:
    Connection status including host, port, connected state, and accounts
    
  Example:
    >>> await get_connection_status()
    {
      "connected": true,
      "host": "localhost",
      "port": 8888,
      "client_id": "103045",
      "accounts": ["DU123456"]
    }
  """
  try:
    logger.debug("Getting connection status")
    status = await ib_interface.get_connection_status()
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
async def reconnect() -> ReconnectResponse:
  """Reconnect to IBKR Gateway/TWS.
  
  Disconnect and reconnect to the IBKR Gateway/TWS. Useful when connection
  is lost or needs to be refreshed.
  
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
  try:
    logger.debug("Attempting to reconnect")
    response = await ib_interface.reconnect()
    return response
  except Exception as e:
    logger.error(f"Error in reconnect: {e}")
    return JSONResponse(
      status_code=500,
      content={"error": str(e), "message": "Failed to reconnect"}
    )
