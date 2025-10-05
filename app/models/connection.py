"""Pydantic models for connection management."""
from pydantic import BaseModel, Field


class ConnectionStatus(BaseModel):
  """Connection status information."""

  connected: bool = Field(..., description="Connection status")
  host: str = Field(..., description="Gateway host")
  port: int = Field(..., description="Gateway port")
  client_id: str | None = Field(None, description="Client ID")
  accounts: list[str] = Field(default_factory=list, description="Connected accounts")


class ReconnectResponse(BaseModel):
  """Response from reconnection attempt."""

  success: bool = Field(..., description="Reconnection success status")
  message: str = Field(..., description="Status message")
  connected: bool = Field(..., description="Current connection status")
