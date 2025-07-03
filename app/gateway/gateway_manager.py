"""Gateway manager for IBKR TWS Gateway."""
from typing import Any
from .docker_service import IBKRGatewayDockerService
from app.core.setup_logging import logger
from app.core.config import get_config

config = get_config()

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
        logger.debug("IBKR Gateway started successfully")
    except Exception:
      logger.exception("Failed to start gateway")
      return False
    else:
      return success

  async def stop_gateway(self) -> bool:
    """Stop the IBKR Gateway container."""
    try:
      success = await self.docker_service.stop_gateway(
        persist=config.ib_gateway_persist,
      )
      if success:
        self.is_running = False
        logger.debug("IBKR Gateway stopped successfully")
    except Exception:
      logger.exception("Failed to stop gateway")
      return False
    else:
      return success

  async def get_gateway_status(self) -> dict[str, Any]:
    """Get the current status of the IBKR Gateway."""
    try:
      container_status = await self.docker_service.get_container_status()
    except Exception as e:
      logger.error(f"Failed to get gateway status: {e}")
      return {
        "is_running": False,
        "error": str(e),
      }
    else:
      return {
        "is_running": self.is_running,
        "container": container_status,
      }

  async def get_gateway_logs(self, tail: int = 100) -> str:
    """Get the logs from the IBKR Gateway container."""
    logs = await self.docker_service.get_container_logs(tail)
    log_lines = [line.strip() for line in logs.split("\n") if line.strip()]
    return {"logs": log_lines}

  async def cleanup(self) -> None:
    """Cleanup resources when shutting down."""
    try:
      if self.is_running:
        await self.stop_gateway()

      # Cleanup docker service resources
      if (hasattr(self, "docker_service") and self.docker_service and
          hasattr(self.docker_service, "client")):
        self.docker_service.client.close()
    except Exception as e:
      logger.error(f"Error during cleanup: {e}")
    finally:
      self.is_running = False

  def __del__(self) -> None:
    """Cleanup when the manager is destroyed."""
    if self.is_running:
      logger.warning(
        "IBKRGatewayManager destroyed while still running. "
        "Call await manager.cleanup() before destruction.",
      )
