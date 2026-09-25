"""Multi-account registry for parallel IBKR Gateway containers.

Accounts are defined in a YAML file (default: ``accounts.yaml`` in the project
root, override with the ``IB_ACCOUNTS_FILE`` env var). Each account runs its
own gateway container on dedicated ports derived from its 0-based position in
the file. API ports use stride 2 because every container maps both its live
and paper API port:

  - IB API host ports: (4001, 4002) + 2 * index  -> account 0: 4001/4002, account 1: 4003/4004
    (client connects to the live or paper port matching its trading_mode)
  - VNC host port:     configured base VNC port + index
  - RDP host port:     configured base RDP port + index
"""

import os
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from app.core.config import get_config
from app.core.setup_logging import logger

# Base host ports. Per-account ports are base + account index.
HOST_LIVE_API_PORT = 4001
HOST_PAPER_API_PORT = 4002

_DEFAULT_ACCOUNTS_FILE = "accounts.yaml"


class UnknownAccountError(LookupError):
  """Raised when an unknown account_id is requested."""


@dataclass(frozen=True)
class AccountConfig:
  """A single IBKR account running its own gateway container."""

  account_id: str
  description: str
  username: str
  trading_mode: str  # "paper" | "live"
  is_default: bool
  index: int  # 0-based position in the accounts file (drives port offsets)

  @property
  def api_port(self) -> int:
    """Host port of this account's IB API endpoint (stride 2 per account)."""
    base = (
      HOST_LIVE_API_PORT if self.trading_mode == "live" else HOST_PAPER_API_PORT
    )
    return base + 2 * self.index

  @property
  def api_host_ports(self) -> tuple[int, int]:
    """(live host port, paper host port) mapped by this account's container."""
    return (
      HOST_LIVE_API_PORT + 2 * self.index,
      HOST_PAPER_API_PORT + 2 * self.index,
    )

  @property
  def vnc_port(self) -> int:
    """Host VNC port of this account's gateway container."""
    return get_config().ib_gateway_vnc_port + self.index

  @property
  def rdp_port(self) -> int:
    """Host RDP port of this account's gateway container."""
    return get_config().tws_rdp_port + self.index

  def public_info(self) -> dict[str, str]:
    """Safe to expose externally (no username)."""
    return {"account_id": self.account_id, "description": self.description}


def is_tws_image() -> bool:
  """True if the configured gateway image exposes RDP (tws-rdesktop)."""
  return "tws-rdesktop" in get_config().ib_gateway_image


def remote_desktop_access(account: AccountConfig) -> tuple[str, int]:
  """Return (type, port) of the account's remote desktop access.

  tws-rdesktop images are accessed via RDP, other images via VNC.
  """
  if is_tws_image():
    return "rdp", account.rdp_port
  return "vnc", account.vnc_port


def _accounts_file_path() -> Path:
  path = os.getenv("IB_ACCOUNTS_FILE", _DEFAULT_ACCOUNTS_FILE)
  return Path(path).expanduser()


class AccountRegistry:
  """Loads and validates the multi-account configuration."""

  def __init__(self, accounts_file: str | Path | None = None) -> None:
    self.accounts_file = Path(accounts_file or _accounts_file_path())
    self.accounts: list[AccountConfig] = self._load()
    self._by_id: dict[str, AccountConfig] = {
      account.account_id: account for account in self.accounts
    }

  def _load(self) -> list[AccountConfig]:
    config = get_config()
    if not self.accounts_file.exists():
      logger.warning(
        f"Accounts file {self.accounts_file} not found. "
        "Falling back to a single default account from IB_GATEWAY_USERNAME."
      )
      return [
        AccountConfig(
          account_id=config.ib_gateway_username,
          description="Default",
          username=config.ib_gateway_username,
          trading_mode=config.ib_gateway_tradingmode,
          is_default=True,
          index=0,
        )
      ]

    data = yaml.safe_load(self.accounts_file.read_text()) or {}
    raw_accounts = data.get("accounts") or []
    if not raw_accounts:
      raise ValueError(
        f"No accounts defined in {self.accounts_file}. "
        "Add at least one entry under the 'accounts' key."
      )

    accounts: list[AccountConfig] = []
    seen_ids: set[str] = set()
    for i, raw in enumerate(raw_accounts):
      account_id = str(raw.get("account_id") or "").strip()
      username = str(raw.get("username") or "").strip()
      if not account_id:
        raise ValueError(
          f"Account #{i + 1} in {self.accounts_file} is missing 'account_id'."
        )
      if not username:
        raise ValueError(
          f"Account '{account_id}' in {self.accounts_file} is missing 'username'."
        )
      if account_id in seen_ids:
        raise ValueError(f"Duplicate account_id '{account_id}' in {self.accounts_file}.")
      seen_ids.add(account_id)

      trading_mode = str(raw.get("trading_mode") or "paper").strip().lower()
      if trading_mode not in ("paper", "live"):
        raise ValueError(
          f"Account '{account_id}' has invalid trading_mode "
          f"'{trading_mode}' (expected 'paper' or 'live')."
        )

      accounts.append(
        AccountConfig(
          account_id=account_id,
          description=str(raw.get("description") or account_id),
          username=username,
          trading_mode=trading_mode,
          is_default=bool(raw.get("default")),
          index=i,
        )
      )

    defaults = [a for a in accounts if a.is_default]
    if len(defaults) > 1:
      raise ValueError(
        "Multiple accounts are flagged as default "
        f"({', '.join(a.account_id for a in defaults)}). "
        "Only one account can be the default."
      )
    if not defaults:
      logger.warning(
        f"No account in {self.accounts_file} is flagged as default; "
        f"using '{accounts[0].account_id}' (first entry)."
      )
      accounts[0] = replace(accounts[0], is_default=True)

    logger.info(
      f"Loaded {len(accounts)} account(s) from {self.accounts_file}: "
      + ", ".join(a.account_id for a in accounts)
    )
    return accounts

  @property
  def default_account(self) -> AccountConfig:
    """Return the account flagged as default (first entry if none)."""
    for account in self.accounts:
      if account.is_default:
        return account
    return self.accounts[0]

  def get(self, account_id: str | None = None) -> AccountConfig:
    """Resolve an account by id; empty/None resolves to the default account."""
    if not account_id or not str(account_id).strip():
      return self.default_account
    key = str(account_id).strip()
    try:
      return self._by_id[key]
    except KeyError:
      available = ", ".join(sorted(self._by_id))
      raise UnknownAccountError(
        f"Unknown account id '{account_id}'. Available accounts: {available}"
      ) from None

  def get_by_username(self, username: str) -> AccountConfig | None:
    for account in self.accounts:
      if account.username == username:
        return account
    return None


_registry: AccountRegistry | None = None


def get_account_registry() -> AccountRegistry:
  """Get the global account registry (singleton)."""
  global _registry
  if _registry is None:
    _registry = AccountRegistry()
  return _registry
