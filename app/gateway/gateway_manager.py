import asyncio
import logging
from typing import Optional, Dict, Any, List
from .docker_service import IBKRGatewayDockerService

logger = logging.getLogger(__name__)


class IBKRGatewayManager:
  """Manager for IBKR Gateway container and interactions."""

  def __init__(self) -> None:
    """Initialize the IBKR Gateway manager."""
    self.docker_service = IBKRGatewayDockerService()
    self.is_running = False

  async def start_gateway(self) -> bool:
    """Start the IBKR Gateway container."""
    try:
      success = await self.docker_service.start_gateway()
      if success:
        self.is_running = True
        logger.info("IBKR Gateway started successfully")
    except Exception:
      logger.exception("Failed to start gateway")
      return False
    else:
      return success

  async def stop_gateway(self) -> bool:
    """Stop the IBKR Gateway container."""
    try:
      success = await self.docker_service.stop_gateway()
      if success:
        self.is_running = False
        logger.info("IBKR Gateway stopped successfully")
    except Exception:
      logger.exception("Failed to stop gateway")
      return False
    else:
      return success

  async def get_gateway_status(self) -> dict[str, Any]:
    """Get the current status of the IBKR Gateway."""
    try:
      container_status = await self.docker_service.get_container_status()

      status = {
        "is_running": self.is_running,
        "gateway_url": self.gateway_url,
        "container": container_status
      }

      # Add health check if container is running
      if container_status.get("status") == "running":
        try:
          import httpx
          async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.gateway_url}/health")
            status["health"] = {
              "status": "healthy" if response.status_code == 200 else "unhealthy",
              "status_code": response.status_code
            }
        except Exception as e:
          status["health"] = {
            "status": "unreachable",
            "error": str(e)
          }

      return status
    except Exception as e:
      logger.error(f"Failed to get gateway status: {e}")
      return {
        "is_running": False,
        "error": str(e)
      }

  async def get_gateway_logs(self, tail: int = 100) -> str:
    """Get the logs from the IBKR Gateway container."""
    return await self.docker_service.get_container_logs(tail)

  async def connect_to_ibkr(
      self,
      host: str = "127.0.0.1",
      port: int = 4001,
      client_id: int = 1) -> bool:
    """Connect to IBKR TWS/Gateway through the container."""
    try:
      if not self.is_running:
        logger.error("Gateway is not running. Start it first.")
        return False

      # This would typically involve making API calls to the gateway
      # to establish connection to IBKR TWS/Gateway
      logger.info(f"Connecting to IBKR at {host}:{port} with client_id {client_id}")

      # Placeholder for actual connection logic
      # You would implement the actual IBKR API connection here

      return True
    except Exception as e:
      logger.error(f"Failed to connect to IBKR: {e}")
      return False

  async def disconnect_from_ibkr(self) -> bool:
    """Disconnect from IBKR TWS/Gateway."""
    try:
      logger.info("Disconnecting from IBKR...")
      # Placeholder for actual disconnection logic
      return True
    except Exception as e:
      logger.error(f"Failed to disconnect from IBKR: {e}")
      return False

  async def get_account_info(self) -> Dict[str, Any]:
    """Get account information from IBKR."""
    try:
      if not self.is_running:
        return {"error": "Gateway is not running"}

      # Placeholder for actual account info retrieval
      # This would make API calls to the gateway to get account data

      return {
        "account_id": "demo_account",
        "account_type": "demo",
        "currency": "USD",
        "status": "active"
      }
    except Exception as e:
      logger.error(f"Failed to get account info: {e}")
      return {"error": str(e)}

  async def get_portfolio(self) -> List[Dict[str, Any]]:
    """Get portfolio positions from IBKR."""
    try:
      if not self.is_running:
        return []

      # Placeholder for actual portfolio retrieval
      # This would make API calls to the gateway to get portfolio data

      return [
        {
          "symbol": "AAPL",
          "quantity": 100,
          "market_value": 15000.0,
          "unrealized_pnl": 500.0
        }
      ]
    except Exception as e:
      logger.error(f"Failed to get portfolio: {e}")
      return []

  async def cleanup(self):
    """Cleanup resources when shutting down."""
    try:
      if self.is_running:
        await self.stop_gateway()
    except Exception as e:
      logger.error(f"Error during cleanup: {e}")

  def __del__(self):
    """Cleanup when the manager is destroyed."""
    # Don't call async methods in __del__
    # The cleanup should be called explicitly before destruction
    pass
