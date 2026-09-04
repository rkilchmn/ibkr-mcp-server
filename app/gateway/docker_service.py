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

VNC_PORT_DOCKER = 5900
ib_gateway_vnc_port = config.ib_gateway_vnc_port
RDP_PORT_DOCKER = 3389
tws_rdp_port = config.tws_rdp_port

# Run container on the host network when NAT is broken on this host.
# Default false: container uses the Docker bridge network.
USE_HOST_NETWORK = os.getenv("IB_GATEWAY_USE_HOST_NETWORK", "false").lower() == "true"

# API ports through socat (host port -> mapped to container port)
# Image-specific container ports, but always mapped to the same host ports:
#   Live: container 4003/7498 -> host 4001
#   Paper: container 4004/7499 -> host 4002
_is_tws_image = "tws-rdesktop" in config.ib_gateway_image
if _is_tws_image:
  CONTAINER_LIVE_API_PORT = 7498
  CONTAINER_PAPER_API_PORT = 7499
else:
  CONTAINER_LIVE_API_PORT = 4003
  CONTAINER_PAPER_API_PORT = 4004
HOST_LIVE_API_PORT = 4001
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
  "image": config.ib_gateway_image,
  "ports": None
  if USE_HOST_NETWORK
  else {
    f"{VNC_PORT_DOCKER}/tcp": [
      {"HostIp": "127.0.0.1", "HostPort": str(ib_gateway_vnc_port)},
    ],
    f"{RDP_PORT_DOCKER}/tcp": [
      {"HostIp": "127.0.0.1", "HostPort": str(tws_rdp_port)},
    ],
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

if config.ib_gateway_vnc_password_file:
  vnc_password_file_host_path = str(
    Path(config.ib_gateway_vnc_password_file).expanduser(),
  )
elif config.ib_gateway_vnc_password:
  vnc_password_file_host_path = None
else:
  vnc_password_file_host_path = str(
    Path(config.ib_gateway_password_path, "vnc_password").expanduser(),
  )

# Configure VNC password: pass the file path through to Docker via a
# read-only bind mount into /run/secrets/vnc_password and set
# VNC_SERVER_PASSWORD_FILE so the container knows where to find it.
if vnc_password_file_host_path:
  docker_config["environment"]["VNC_SERVER_PASSWORD_FILE"] = (
    f"{CONTAINER_SECRETS_PATH}/vnc_password"
  )
  _vnc_secret_src = Path(vnc_password_file_host_path)
  if not _vnc_secret_src.exists():
    logger.warning(
      f"VNC password file {_vnc_secret_src} does not exist. "
      "The container may fail to start without it.",
    )
  else:
    docker_config["volumes"][str(_vnc_secret_src)] = {
      "bind": f"{CONTAINER_SECRETS_PATH}/vnc_password",
      "mode": "ro",
    }
    logger.debug(
      f"Bind-mounted {vnc_password_file_host_path} -> "
      f"{CONTAINER_SECRETS_PATH}/vnc_password",
    )
elif config.ib_gateway_vnc_password:
  docker_config["environment"]["VNC_SERVER_PASSWORD"] = config.ib_gateway_vnc_password

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

# Determine the abc password file host path
if config.password_file:
  abc_password_file_host_path = str(
    Path(config.password_file).expanduser(),
  )
else:
  abc_password_file_host_path = str(
    Path(config.ib_gateway_password_path, "abc_password").expanduser(),
  )

# Configure abc password: pass the file path through to Docker via a
# read-only bind mount into /run/secrets/abc_password and set PASSWD_FILE
# so the container knows where to find it.
if abc_password_file_host_path:
  docker_config["environment"]["PASSWD_FILE"] = f"{CONTAINER_SECRETS_PATH}/abc_password"
  _abc_secret_src = Path(abc_password_file_host_path)
  if not _abc_secret_src.exists():
    logger.warning(
      f"abc_password file {_abc_secret_src} does not exist. "
      "The container may fail to start without it.",
    )
  else:
    docker_config["volumes"][str(_abc_secret_src)] = {
      "bind": f"{CONTAINER_SECRETS_PATH}/abc_password",
      "mode": "ro",
    }
    logger.debug(
      f"Bind-mounted {abc_password_file_host_path} -> "
      f"{CONTAINER_SECRETS_PATH}/abc_password",
    )

# Log summary of all secret file bind mounts
_secret_mappings = []
for _host_path, _vol_config in docker_config["volumes"].items():
  _secret_mappings.append(f"{_host_path} -> {_vol_config['bind']}")
if _secret_mappings:
  logger.info(f"Secret files mapped: {', '.join(_secret_mappings)}")


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

  def _pull_image_with_progress(self, image_name: str) -> None:
    """Pull a Docker image and log download progress."""
    for chunk in self.client.api.pull(image_name, stream=True, decode=True):
      if "id" in chunk and "progress" in chunk:
        logger.info(f"  [{chunk['id']}] {chunk['status']} {chunk['progress']}")
      elif "status" in chunk:
        logger.info(f"  {chunk['status']}")

  async def start_gateway(self) -> bool:
    """Start the IBKR Gateway container."""
    try:
      # Check if container already exists
      try:
        existing_container = self.client.containers.get(self.container_name)
        if existing_container.status == "running":
          running_image = existing_container.attrs["Config"]["Image"]
          requested_image = docker_config["image"]
          if running_image == requested_image:
            logger.debug(
              f"Container {self.container_name} is already running "
              f'with image "{requested_image}"',
            )
            self.container = existing_container
            return True
          # Image mismatch — stop and remove the old container
          logger.info(
            f"Container {self.container_name} is running with image "
            f'"{running_image}", but "{requested_image}" was requested; restarting',
          )
          existing_container.stop(timeout=self._connection_timeout)
          existing_container.remove()
        else:
          existing_container.remove()
      except docker.errors.NotFound:
        pass

      # Check if the image exists locally, pull only if missing
      try:
        self.client.images.get(docker_config["image"])
        logger.debug(f'Image "{docker_config["image"]}" found locally')
      except docker.errors.ImageNotFound:
        logger.info(f'Image "{docker_config["image"]}" not found locally, pulling...')
        self._pull_image_with_progress(docker_config["image"])
        logger.info(f'Image "{docker_config["image"]}" pulled successfully')

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
      logger.info(
        f'Starting IBKR Gateway container using image: "{docker_config["image"]}"',
      )
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
        self._health_check_interval - (current_time - self._last_health_check),
      )

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
