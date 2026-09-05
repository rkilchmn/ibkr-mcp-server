"""Docker service for the IBKR Gateway."""

import hashlib
import os
import time
import asyncio
import docker
import yaml
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
    "TRADING_MODE": config.ib_gateway_tradingmode,
    "READ_ONLY_API": "yes" if config.ib_gateway_readonly else "no",
    "AUTO_RESTART_TIME": os.getenv("IB_GATEWAY_AUTO_RESTART_TIME", ""),
  },
  "volumes": {},
}

# Pass through image-defined env vars from the host environment only if
# they are explicitly set. If not set, the container applies its own
# defaults.
_PASSTHROUGH_ENV_VARS = [
  "TWS_ACCEPT_INCOMING",
  "TWOFA_TIMEOUT_ACTION",
  "TWOFA_DEVICE",
  "TWOFA_EXIT_INTERVAL",
  "RELOGIN_AFTER_TWOFA_TIMEOUT",
  "EXISTING_SESSION_DETECTED_ACTION",
  "BYPASS_WARNING",
  "ALLOW_BLIND_TRADING",
  "AUTO_LOGOFF_TIME",
  "TWS_COLD_RESTART",
  "SAVE_TWS_SETTINGS",
  "TIME_ZONE",
  "TWS_SETTINGS_PATH",
  "TWS_MASTER_CLIENT_ID",
  "JAVA_HEAP_SIZE",
  "SSH_TUNNEL",
  "SSH_OPTIONS",
  "SSH_ALIVE_INTERVAL",
  "SSH_ALIVE_COUNT",
  "SSH_PASSPHRASE",
  "SSH_PASSPHRASE_FILE",
  "SSH_REMOTE_PORT",
  "SSH_USER_TUNNEL",
  "SSH_RESTART",
  "SSH_VNC_PORT",
  "SSH_RDP_PORT",
  "PUID",
  "PGID",
  "PASSWD",
  "PASSWD_FILE",
  "START_SCRIPTS",
  "X_SCRIPTS",
  "IBC_SCRIPTS",
  "CUSTOM_CONFIG",
  "TWS_USERID_PAPER",
  "TWS_PASSWORD_PAPER",
  "TWS_PASSWORD_PAPER_FILE",
]

for _env_var in _PASSTHROUGH_ENV_VARS:
  _host_value = os.getenv(_env_var)
  if _host_value is not None:
    docker_config["environment"][_env_var] = _host_value

# Configure TWS settings persistence volume.
# Defaults per image:
#   ib-gateway: host ./tws_settings -> container /home/ibgateway/tws_settings
#   tws-rdesktop: host ./config -> container /config
_tws_settings_host_path = config.ib_gateway_tws_settings_path
if _tws_settings_host_path:
  _tws_settings_host_path = str(Path(_tws_settings_host_path).expanduser())

if _is_tws_image:
  _default_tws_settings_container_path = "/config"
  _default_tws_settings_host_path = str(Path("config").resolve())
else:
  _default_tws_settings_container_path = "/home/ibkr/tws_settings"
  _default_tws_settings_host_path = str(Path("tws_settings").resolve())

_tws_settings_container_path = _default_tws_settings_container_path
if not _tws_settings_host_path:
  _tws_settings_host_path = _default_tws_settings_host_path

docker_config["environment"]["TWS_SETTINGS_PATH"] = _tws_settings_container_path
docker_config["volumes"][_tws_settings_host_path] = {
  "bind": _tws_settings_container_path,
  "mode": "rw",
}
logger.debug(
  f"Bind-mounted {_tws_settings_host_path} -> "
  f"{_tws_settings_container_path} for TWS settings persistence"
)

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
    self._compose_dir = Path(".docker")
    self._compose_file = self._compose_dir / "docker-compose.yml"
    self._compose_last_success = self._compose_dir / "docker-compose.last-success.yml"

  def _get_compose_paths(self) -> tuple[Path, Path]:
    """Return the current and last-success compose file paths."""
    return self._compose_file, self._compose_last_success

  def _generate_compose(self, docker_config: dict[str, Any]) -> dict[str, Any]:
    """Generate a docker-compose dict from the current docker_config."""
    ports = docker_config.get("ports") or {}
    environment = dict(docker_config.get("environment") or {})
    volumes = docker_config.get("volumes") or {}

    services: dict[str, Any] = {
      "ibkr-gateway": {
        "image": docker_config["image"],
        "container_name": self.container_name,
        "environment": environment,
        "volumes": [],
        "ports": [],
        "restart": "unless-stopped",
      }
    }

    if USE_HOST_NETWORK:
      services["ibkr-gateway"]["network_mode"] = "host"
    else:
      for container_port, host_bindings in ports.items():
        port_number = container_port.replace("/tcp", "")
        for binding in host_bindings:
          host_port = binding.get("HostPort", port_number)
          host_ip = binding.get("HostIp", "127.0.0.1")
          services["ibkr-gateway"]["ports"].append(
            f"{host_ip}:{host_port}:{port_number}"
          )

    for host_path, vol_config in volumes.items():
      bind = vol_config.get("bind", host_path)
      mode = vol_config.get("mode", "rw")
      services["ibkr-gateway"]["volumes"].append(
        f"{host_path}:{bind}:{mode}"
      )

    return {"services": services}

  def _write_compose(self, compose: dict[str, Any], path: Path) -> None:
    """Write compose dict to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(compose, sort_keys=False))

  def _compose_fingerprint(self, docker_config: dict[str, Any]) -> str:
    """Return a stable fingerprint for the generated compose content."""
    compose = self._generate_compose(docker_config)
    payload = yaml.safe_dump(compose, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()

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
      current_compose, last_success = self._get_compose_paths()
      new_compose = self._generate_compose(docker_config)
      new_content = yaml.safe_dump(new_compose, sort_keys=False)
      new_hash = hashlib.sha256(new_content.encode()).hexdigest()

      old_hash = None
      if last_success.exists():
        old_hash = hashlib.sha256(last_success.read_bytes()).hexdigest()

      config_changed = old_hash != new_hash

      if config_changed:
        logger.info("Generated compose differs from last success; rotating")
        try:
          existing_container = self.client.containers.get(self.container_name)
          if existing_container.status == "running":
            logger.info("Stopping running container before compose rotation")
            existing_container.stop(timeout=self._connection_timeout)
          existing_container.remove()
        except docker.errors.NotFound:
          pass

        if last_success.exists():
          backup = last_success.with_suffix(".last-success.bak")
          if backup.exists():
            backup.unlink()
          last_success.replace(backup)

        self._write_compose(new_compose, current_compose)
        logger.info(f"Wrote new compose file: {current_compose}")

      try:
        existing_container = self.client.containers.get(self.container_name)
        if existing_container.status == "running":
          running_image = existing_container.attrs["Config"]["Image"]
          requested_image = docker_config["image"]
          if running_image == requested_image and not config_changed:
            logger.debug(
              f"Container {self.container_name} is already running "
              f'with image "{requested_image}"',
            )
            self.container = existing_container
            return True
          logger.info(
            f"Container {self.container_name} running with image "
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

      # Persist compose on successful start
      self._write_compose(new_compose, last_success)
      logger.info(f"Persisted successful compose file: {last_success}")

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
