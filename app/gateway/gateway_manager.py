"""Gateway manager for IBKR TWS Gateway containers (one per account)."""

import asyncio
from typing import Any

from .docker_service import IBKRGatewayDockerService
from app.core.accounts import (
  AccountConfig,
  get_account_registry,
  remote_desktop_access,
)
from app.core.setup_logging import logger
from app.core.config import get_config

config = get_config()


class IBKRGatewayManager:
  """Manages one gateway container per configured account.

  Each account runs in a separate Docker container on dedicated ports so
  multiple accounts can be used in parallel without interfering.
  """

  def __init__(self) -> None:
    """Initialize the gateway manager with one docker service per account."""
    self.registry = get_account_registry()
    self.docker_services: dict[str, IBKRGatewayDockerService] = {}
    for account in self.registry.accounts:
      self.docker_services[account.account_id] = IBKRGatewayDockerService(
        username=account.username,
        port_index=account.index,
        trading_mode=account.trading_mode,
        container_name=f"ibkr-gateway-{account.username}",
      )
    self.is_running: dict[str, bool] = {
      account.account_id: False for account in self.registry.accounts
    }

  def _service(self, account_id: str | None = None) -> tuple[AccountConfig, IBKRGatewayDockerService]:
    """Resolve the docker service for an account (default when not specified)."""
    account = self.registry.get(account_id)
    return account, self.docker_services[account.account_id]

  async def start_gateway(self, account_id: str | None = None) -> bool:
    """Start the IBKR Gateway container for an account (default if omitted)."""
    try:
      account, service = self._service(account_id)
      success = await service.start_gateway()
      if success:
        self.is_running[account.account_id] = True
        logger.debug(
          f"IBKR Gateway for account {account.account_id} started successfully"
        )
    except Exception:
      logger.exception(f"Failed to start gateway for account: {account_id}")
      return False
    else:
      return success

  async def start_all_gateways(self) -> dict[str, bool]:
    """Start the gateways of all configured accounts in parallel."""
    results = await asyncio.gather(
      *[self.start_gateway(account.account_id) for account in self.registry.accounts]
    )
    status = {
      account.account_id: success
      for account, success in zip(self.registry.accounts, results)
    }
    logger.info(f"Gateway startup results: {status}")
    return status

  async def stop_gateway(self, account_id: str | None = None) -> bool:
    """Stop the IBKR Gateway container for an account (default if omitted)."""
    try:
      account, service = self._service(account_id)
      success = await service.stop_gateway(persist=config.ib_gateway_persist)
      if success:
        self.is_running[account.account_id] = False
        logger.debug(f"IBKR Gateway for account {account.account_id} stopped")
    except Exception:
      logger.exception(f"Failed to stop gateway for account: {account_id}")
      return False
    else:
      return success

  async def restart_gateway_with_user(self, username: str) -> bool:
    """Restart the gateway of the account registered under this username."""
    try:
      account = self.registry.get_by_username(username)
      if account is None:
        logger.error(f"Unknown gateway username: {username}")
        return False
      await self.stop_gateway(account.account_id)
      success = await self.start_gateway(account.account_id)
      if success:
        logger.debug(
          f"IBKR Gateway restarted for account {account.account_id} (user {username})"
        )
      return success
    except Exception:
      logger.exception(f"Failed to restart gateway with username: {username}")
      return False

  async def get_gateway_status(self) -> dict[str, Any]:
    """Get the status of all account gateways.

    Only account_id and description are exposed per account (usernames stay
    private), plus the account's remote desktop port (RDP for tws-rdesktop
    images, VNC otherwise).

    """
    entries: list[dict[str, Any]] = []
    for account in self.registry.accounts:
      service = self.docker_services[account.account_id]
      try:
        container_status = await service.get_container_status()
      except Exception as e:
        logger.error(f"Failed to get gateway status for {account.account_id}: {e}")
        container_status = {"status": "error", "health": "unknown"}

      access_type, _access_port = remote_desktop_access(account)
      entry: dict[str, Any] = {
        **account.public_info(),
        "is_running": (
          self.is_running[account.account_id]
          or container_status.get("status") == "running"
        ),
        "vnc_port": account.vnc_port if access_type == "vnc" else None,
        "rdp_port": account.rdp_port if access_type == "rdp" else None,
        "container": container_status,
      }
      entries.append(entry)

    return {"accounts": entries}

  async def get_gateway_logs(
    self, tail: int = 100, account_id: str | None = None,
  ) -> dict[str, Any]:
    """Get the logs of an account's IBKR Gateway container."""
    account, service = self._service(account_id)
    logs = await service.get_container_logs(tail)
    log_lines = [line.strip() for line in logs.split("\n") if line.strip()]
    return {"logs": log_lines}

  async def cleanup(self) -> None:
    """Cleanup resources when shutting down (all account gateways)."""
    if config.mode == "DEV":
      logger.info("Dev mode: Keeping IBKR Gateways running...")
      return
    try:
      await asyncio.gather(
        *[self.stop_gateway(account.account_id) for account in self.registry.accounts]
      )

      # Cleanup docker service resources
      for service in self.docker_services.values():
        if hasattr(service, "client") and service.client:
          service.client.close()
    except Exception as e:
      logger.error(f"Error during cleanup: {e}")
    finally:
      for account_id in self.is_running:
        self.is_running[account_id] = False

  def __del__(self) -> None:
    """Cleanup when the manager is destroyed."""
    if any(self.is_running.values()):
      logger.warning(
        "IBKRGatewayManager destroyed while still running. "
        "Call await manager.cleanup() before destruction.",
      )
