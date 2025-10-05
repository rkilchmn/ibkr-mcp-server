"""Connection management service."""
import asyncio
from app.services.client import IBClient
from app.core.setup_logging import logger
from app.models import ConnectionStatus, ReconnectResponse
from app.core.config import get_config


class ConnectionClient(IBClient):
  """Connection management operations."""

  async def get_connection_status(self) -> ConnectionStatus:
    """Get current connection status.
    
    Returns:
      Connection status information
    """
    config = get_config()
    
    try:
      is_connected = self.ib.isConnected()
      
      # Get accounts if connected
      accounts = []
      if is_connected:
        try:
          accounts = self.ib.managedAccounts()
        except Exception as e:
          logger.debug(f"Could not get accounts: {e}")
      
      return ConnectionStatus(
        connected=is_connected,
        host=config.ib_gateway_host,
        port=config.ib_gateway_port,
        client_id=None,  # Client ID is dynamic per connection
        accounts=accounts if accounts else []
      )
    except Exception as e:
      logger.error(f"Failed to get connection status: {e}")
      return ConnectionStatus(
        connected=False,
        host=config.ib_gateway_host,
        port=config.ib_gateway_port,
        client_id=None,
        accounts=[]
      )

  async def reconnect(self) -> ReconnectResponse:
    """Attempt to reconnect to IBKR Gateway.
    
    Returns:
      Reconnection response with status
    """
    try:
      # Disconnect if currently connected
      if self.ib.isConnected():
        logger.info("Disconnecting from IBKR Gateway...")
        self.ib.disconnect()
        await asyncio.sleep(1)
      
      # Attempt to reconnect
      logger.info("Attempting to reconnect to IBKR Gateway...")
      await self._connect()
      
      is_connected = self.ib.isConnected()
      
      if is_connected:
        return ReconnectResponse(
          success=True,
          message="Successfully reconnected to IBKR Gateway",
          connected=True
        )
      else:
        return ReconnectResponse(
          success=False,
          message="Failed to reconnect to IBKR Gateway",
          connected=False
        )
      
    except Exception as e:
      logger.error(f"Reconnection failed: {e}")
      return ReconnectResponse(
        success=False,
        message=f"Reconnection error: {str(e)}",
        connected=False
      )
