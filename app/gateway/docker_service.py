"""Docker service for the IBKR Gateway."""

import os
import time
import asyncio
import docker
from pathlib import Path
from datetime import datetime, UTC
from ib_async import IB
from typing import Any
from app.core.setup_logging import logger
from app.core.config import get_config

config = get_config()

VNC_PORT = 5900
VNC_HOST_PORT = config.ib_gateway_vnc_port

# Run container on the host network when NAT is broken on this host.
# Default false: container uses the Docker bridge network.
USE_HOST_NETWORK = os.getenv("IB_GATEWAY_USE_HOST_NETWORK", "false").lower() == "true"

# API ports through socat (host port → mapped to container port)
# gnzsnz/ib-gateway-docker exposes:
#   4003 → container live API,  4001 → host
#   4004 → container paper API, 4002 → host
CONTAINER_LIVE_API_PORT = 4003
HOST_LIVE_API_PORT = 4001
CONTAINER_PAPER_API_PORT = 4004
HOST_PAPER_API_PORT = 4002

if config.ib_gateway_tradingmode == "live":
  API_PORT = HOST_LIVE_API_PORT
else:
  API_PORT = HOST_PAPER_API_PORT

CONTAINER_SECRETS_PATH = "/run/secrets"

# Determine the password file host path
password_file_host_path: str | None = None
if config.ib_gateway_password_file:
  password_file_host_path = str(Path(config.ib_gateway_password_file).expanduser())
elif config.ib_gateway_password:
  password_file_host_path = None
else:
  password_file_host_path = str(
    Path(config.ib_gateway_password_path, config.ib_gateway_username).expanduser(),
  )

if password_file_host_path:
  path_obj = Path(password_file_host_path)
  if not path_obj.exists():
    logger.warning(
      f"Password file {password_file_host_path} does not exist. "
      f"The container may fail to start without credentials.",
    )

docker_config = {
  "image": "ghcr.io/gnzsnz/ib-gateway:stable",
  "ports": None if USE_HOST_NETWORK else {
    f"{VNC_PORT}/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(VNC_HOST_PORT)}],
    f"{CONTAINER_LIVE_API_PORT}/tcp": [
      {"HostIp": "127.0.0.1", "HostPort": str(HOST_LIVE_API_PORT)},
    ],
    f"{CONTAINER_PAPER_API_PORT}/tcp": [
      {"HostIp": "127.0.0.1", "HostPort": str(HOST_PAPER_API_PORT)},
    ],
  },
  "environment": {
    "TWS_USERID": config.ib_gateway_username,
    "TWOFA_TIMEOUT_ACTION": "restart",
    "TRADING_MODE": config.ib_gateway_tradingmode,
    "READ_ONLY_API": "yes" if config.ib_gateway_readonly else "no",
    "RELOGIN_AFTER_TWOFA_TIMEOUT": "yes",
    "AUTO_RESTART_TIME": os.getenv("IB_GATEWAY_AUTO_RESTART_TIME", ""),
    "TWS_ACCEPT_INCOMING": "accept",
    "EXISTING_SESSION_DETECTED_ACTION": "primary",
  },
  "volumes": {},
}

if config.ib_gateway_vnc_password:
  docker_config["environment"]["VNC_SERVER_PASSWORD"] = (
    config.ib_gateway_vnc_password
  )

# Configure credentials: pass the password file path through to Docker
# via a read-only bind mount into /run/secrets/tws_password. The MCP
# process does not need to read the file — only Docker and the
# container's IBC do.
if password_file_host_path:
  docker_config["environment"]["TWS_PASSWORD_FILE"] = (
    f"{CONTAINER_SECRETS_PATH}/tws_password"
  )
  _secret_src = Path(password_file_host_path)
  if not _secret_src.exists():
    logger.warning(
      f"Password file {password_file_host_path} does not exist. "
      "The container may fail to start without credentials.",
    )
  else:
    # The MCP process doesn't need to read the file — only Docker does,
    # for the bind mount. The container's IBC reads it at runtime.
    docker_config["volumes"][str(_secret_src)] = {
      "bind": f"{CONTAINER_SECRETS_PATH}/tws_password",
      "mode": "ro",
    }
    logger.debug(
      f"Bind-mounted {password_file_host_path} -> "
      f"{CONTAINER_SECRETS_PATH}/tws_password",
    )
elif config.ib_gateway_password:
  docker_config["environment"]["TWS_PASSWORD"] = config.ib_gateway_password


class IBKRGatewayDockerService:
  """Service for managing IBKR Gateway Docker container."""

  def __init__(self) -> None:
    """Initialize the IBKR Gateway Docker service."""
    self.client = docker.from_env()
    self.container_name = "ibkr-gateway"
    self.container: docker.models.containers.Container | None = None
    self._health_check_semaphore = asyncio.Semaphore(1)
    self._last_health_check = 0
    self._health_check_interval = 2
    self._connection_timeout = config.ib_connection_timeout
    self._gateway_timeout = config.ib_gateway_timeout

  async def start_gateway(self) -> bool:
    """Start the IBKR Gateway container."""
    try:
      # Check if container already exists
      try:
        existing_container = self.client.containers.get(self.container_name)
        if existing_container.status == "running":
          logger.debug(f"Container {self.container_name} is already running")
          self.container = existing_container
          return True
        existing_container.remove()
      except docker.errors.NotFound:
        pass

      # Check if the image exists locally, pull only if missing
      try:
        self.client.images.get(docker_config["image"])
        logger.debug(f"Image {docker_config['image']} found locally")
      except docker.errors.ImageNotFound:
        logger.debug(f"Image {docker_config['image']} not found locally, pulling...")
        self.client.images.pull(docker_config["image"])
        logger.debug(f"Image {docker_config['image']} pulled successfully")

      # Container configuration
      container_config = {
        "image": docker_config["image"],
        "name": self.container_name,
        "environment": docker_config["environment"],
        "volumes": docker_config["volumes"],
        "detach": True,
        "restart_policy": {"Name": "unless-stopped"},
      }
      if USE_HOST_NETWORK:
        container_config["network_mode"] = "host"
      else:
        container_config["ports"] = docker_config["ports"]

      # Start the container
      logger.debug("Starting IBKR Gateway container...")
      self.container = self.client.containers.run(**container_config)

      # Wait for container to be ready
      if not await self.wait_for_container_ready():
        logger.error("Container failed to become ready")
        return False

    except Exception:
      logger.exception("Failed to start IBKR Gateway container")
      return False
    else:
      logger.debug("IBKR Gateway container started successfully")
      return True

  async def health_check(self) -> bool:
    """Check if the IBKR Gateway container is running (non-blocking, async)."""
    current_time = time.time()

    # Rate limiting: don't check too frequently
    if current_time - self._last_health_check < self._health_check_interval:
      await asyncio.sleep(
        self._health_check_interval - (current_time - self._last_health_check))

    async with self._health_check_semaphore:
      self._last_health_check = time.time()
      return await self._sync_health_check()

  async def _sync_health_check(self) -> bool:
    """Check health asynchronously."""
    ib = None
    try:
      ib = IB()
      await ib.connectAsync("127.0.0.1", API_PORT, 1111)
      return ib.isConnected()
    except Exception:
      return False
    finally:
      if ib:
        ib.disconnect()

  async def wait_for_container_ready(self) -> bool:
    """Wait for the IBKR Gateway container to be ready."""
    timer = 0
    while not await self.health_check():
      if timer > self._gateway_timeout:
        logger.error(f"IBKR Gateway not ready after {self._gateway_timeout} seconds")
        return False
      await asyncio.sleep(2)
      timer += 2
    logger.debug(f"IBKR Gateway container is ready after {timer} seconds")
    return True

  async def get_container_status(self) -> dict[str, Any]:
    """Get the status of the IBKR Gateway container."""
    try:
      # Check if container exists and get its status
      if self.container:
        logger.debug("Getting container status from existing container")
        container_info = self.container.attrs
      else:
        try:
          container = self.client.containers.get(self.container_name)
          container_info = container.attrs
        except docker.errors.NotFound:
          return {
            "status": "not_found",
            "health": "unknown",
            "created": None,
            "started": None,
            "finished": None,
            "age": None,
          }

      # Extract container state information
      state = container_info["State"]
      status = state["Status"]

      # Get timestamps
      created = container_info.get("Created")
      started = state.get("StartedAt")
      finished = state.get("FinishedAt")
      created_time = datetime.fromisoformat(created)
      age = (datetime.now(UTC) - created_time).total_seconds()

      # Perform health check if container is running
      health_status = "unknown"
      if status == "running":
        try:
          is_healthy = await self.health_check()
          health_status = "healthy" if is_healthy else "unhealthy"
        except Exception:
          health_status = "health_check_failed"

    except Exception:
      logger.exception("Failed to get container status")
      return {
        "status": "error",
        "health": "unknown",
        "created": None,
        "started": None,
        "finished": None,
        "age": None,
      }
    else:
      return {
        "status": status,
        "health": health_status,
        "created": created,
        "started": started,
        "finished": finished,
        "age": age,
      }

  async def get_container_logs(self, tail: int = 100) -> str:
    """Get the logs from the IBKR Gateway container."""
    if self.container:
      return self.container.logs(tail=tail).decode("utf-8")
    return "Container not found"

  async def stop_gateway(self, *, persist: bool = False) -> bool:
    """Stop the IBKR Gateway container."""
    if persist:
      logger.debug("Persisting IBKR Gateway container")
      return True

    try:
      if self.container:
        logger.debug("Stopping IBKR Gateway container...")
        self.container.stop(timeout=self._connection_timeout)
        self.container.remove()
        self.container = None
        logger.debug("IBKR Gateway container stopped and removed")
        return True
      try:
        container = self.client.containers.get(self.container_name)
        container.stop(timeout=self._connection_timeout)
        container.remove()
        logger.debug("IBKR Gateway container stopped and removed")
      except docker.errors.NotFound:
        logger.debug("No IBKR Gateway container found to stop")
        return True
    except Exception:
      logger.exception("Failed to stop IBKR Gateway container")
      return False
    else:
      return True

  def __del__(self) -> None:
    """Cleanup when the service is destroyed."""
    try:
      if hasattr(self, "client"):
        self.client.close()
    except Exception:
      logger.exception("Failed to cleanup IBKR Gateway Docker service")
