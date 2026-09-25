"""Pydantic models for connection management."""
from pydantic import BaseModel, Field


class ConnectionStatus(BaseModel):
  """Connection status information."""

  connected: bool = Field(..., description="Connection status")
  host: str = Field(..., description="Gateway host")
  port: int = Field(..., description="Gateway port")
  client_id: str | None = Field(None, description="Client ID")
  accounts: list[str] = Field(default_factory=list, description="Connected IBKR account IDs")
  account_id: str | None = Field(
    None,
    description="Account (account id from /gateway/status) this connection belongs to. Empty/None means the default account.", #noqa: E501
  )
  vnc_port: int | None = Field(
    None,
    description="Host port for VNC access to this account's gateway container (set when using an ib-gateway image)", #noqa: E501
  )
  rdp_port: int | None = Field(
    None,
    description="Host port for RDP access to this account's gateway container (set when using a tws-rdesktop image)", #noqa: E501
  )


class ReconnectResponse(BaseModel):
  """Response from reconnection attempt."""

  success: bool = Field(..., description="Reconnection success status")
  message: str = Field(..., description="Status message")
  connected: bool = Field(..., description="Current connection status")
