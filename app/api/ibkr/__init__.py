"""Endpoints for the IBKR MCP server."""
from fastapi import APIRouter, HTTPException
from app.core.accounts import get_account_registry
from app.core.config import get_config
from app.services.interfaces import IBInterface

ibkr_router = APIRouter(prefix="/ibkr", tags=["ibkr"])


class IBInterfaceManager:
  """One IBInterface (one gateway connection) per configured account."""

  def __init__(self) -> None:
    self.registry = get_account_registry()
    self._config = get_config()
    self._interfaces: dict[str, IBInterface] = {}

  def get(self, account_id: str | None = None) -> IBInterface:
    """Get the interface for an account (default account when not specified)."""
    account = self.registry.get(account_id)
    if account.account_id not in self._interfaces:
      interface = IBInterface()
      interface.host = self._config.ib_gateway_host
      interface.port = account.api_port
      self._interfaces[account.account_id] = interface
    return self._interfaces[account.account_id]


# Per-account interface manager (shared by all endpoints)
ib_interfaces = IBInterfaceManager()


def resolve_interface(account_id: str | None = None) -> IBInterface:
  """Resolve an IB interface by account id, or raise HTTP 404 if unknown."""
  try:
    return ib_interfaces.get(account_id)
  except LookupError as e:
    raise HTTPException(status_code=404, detail=str(e)) from e


# Import all endpoints
from .positions import *
from .contracts import *
from .scanners import *
from .market_data import *
from .fundamental import *
from .account import *
from .trading import *
from .connection import *
