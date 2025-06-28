import docker
import asyncio
import logging
from typing import Optional, Dict, Any
from app.core.config import get_config

logger = logging.getLogger(__name__)

config = get_config()
logger.info(f"Config: {config}")

docker_config = {
  "image": "ghcr.io/extrange/ibkr:stable",
  "ports": {
    6080: 6080,
    8888: 8888,
    7462: 7462,
  },
  "environment": {
    "USERNAME": config.ibkr_gateway_username,
    "PASSWORD": config.ibkr_gateway_password,
    "TWOFA_TIMEOUT_ACTION": "restart",
    "GATEWAY_OR_TWS": "gateway",
    "IBC_TradingMode": "live",
    "IBC_ReadOnlyApi": "no",
    "IBC_ReloginAfterSecondFactorAuthenticationTimeout": "yes",
    "IBC_AutoRestartTime": "08:35 AM",
    "IBC_CommandServerPort": "7462",
    "IBC_ControlFrom": "172.18.0.1",
    "IBC_BindAddress": "0.0.0.0",
  },
}

class IBKRGatewayDockerService:
  """Service for managing IBKR Gateway Docker container."""

  def __init__(self, container_name: str = "ibkr-gateway"):
    self.client = docker.from_env()
    self.container_name = container_name
    self.container: Optional[docker.models.containers.Container] = None

  async def start_gateway(
      self,
      port: int = 5000,
      read_only_api: bool = True,
      ibkr_version: str = "latest") -> bool:
    """Start the IBKR Gateway container."""
    try:
      # Check if container already exists
      try:
        existing_container = self.client.containers.get(self.container_name)
        if existing_container.status == "running":
          logger.info(f"Container {self.container_name} is already running")
          self.container = existing_container
          return True
        elif existing_container.status == "exited":
          existing_container.remove()
      except docker.errors.NotFound:
        pass

      # Pull the IBKR Gateway image
      self.client.images.pull(docker_config["image"])

      # Container configuration
      container_config = {
        "image": docker_config["image"],
        "name": self.container_name,
        "ports": docker_config["ports"],
        "environment": docker_config["environment"],
        "detach": True,
        "restart_policy": {"Name": "unless-stopped"},
      }

      # Start the container
      logger.info("Starting IBKR Gateway container...")
      self.container = self.client.containers.run(**container_config)

      # Wait for container to be ready
      await self._wait_for_container_ready()

      logger.info(f"IBKR Gateway container started successfully on port {port}")
      return True

    except Exception as e:
      logger.error(f"Failed to start IBKR Gateway container: {e}")
      return False

  async def stop_gateway(self) -> bool:
    """Stop the IBKR Gateway container."""
    try:
      if self.container:
        logger.info("Stopping IBKR Gateway container...")
        self.container.stop(timeout=30)
        self.container.remove()
        self.container = None
        logger.info("IBKR Gateway container stopped and removed")
        return True
      else:
        # Try to find and stop container by name
        try:
          container = self.client.containers.get(self.container_name)
          container.stop(timeout=30)
          container.remove()
          logger.info("IBKR Gateway container stopped and removed")
          return True
        except docker.errors.NotFound:
          logger.info("No IBKR Gateway container found to stop")
          return True
    except Exception as e:
      logger.error(f"Failed to stop IBKR Gateway container: {e}")
      return False

  async def get_container_status(self) -> Dict[str, Any]:
    """Get the current status of the IBKR Gateway container."""
    try:
      if self.container:
        self.container.reload()
        return {
          "name": self.container.name,
          "status": self.container.status,
          "ports": self.container.ports,
          "created": self.container.attrs["Created"],
          "image": self.container.image.tags[0] if self.container.image.tags else self.container.image.id
        }
      else:
        try:
          container = self.client.containers.get(self.container_name)
          container.reload()
          return {
            "name": container.name,
            "status": container.status,
            "ports": container.ports,
            "created": container.attrs["Created"],
            "image": container.image.tags[0] if container.image.tags else container.image.id
          }
        except docker.errors.NotFound:
          return {"status": "not_found"}
    except Exception as e:
      logger.error(f"Failed to get container status: {e}")
      return {"status": "error", "message": str(e)}

  async def get_container_logs(self, tail: int = 100) -> str:
    """Get the logs from the IBKR Gateway container."""
    try:
      if self.container:
        return self.container.logs(tail=tail, timestamps=True).decode('utf-8')
      else:
        try:
          container = self.client.containers.get(self.container_name)
          return container.logs(tail=tail, timestamps=True).decode('utf-8')
        except docker.errors.NotFound:
          return "Container not found"
    except Exception as e:
      logger.error(f"Failed to get container logs: {e}")
      return f"Error getting logs: {e}"

  async def _wait_for_container_ready(self, timeout: int = 60) -> None:
    """Wait for the container to be ready and healthy."""
    start_time = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start_time < timeout:
      if self.container:
        self.container.reload()
        if self.container.status == "running":
          # Check if the gateway is responding
          try:
            # Simple health check - you might want to customize this
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
              response = await client.get("http://localhost:5000/health")
              if response.status_code == 200:
                logger.info("IBKR Gateway is ready and responding")
                return
          except Exception:
            pass

      await asyncio.sleep(2)

    logger.warning("Container ready timeout reached")

  def __del__(self):
    """Cleanup when the service is destroyed."""
    try:
      if hasattr(self, 'client'):
        self.client.close()
    except:
      pass
