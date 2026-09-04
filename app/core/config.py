"""Configuration for the application."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
  """Global configuration for the application."""

  ib_gateway_username: str
  ib_gateway_password: str | None = None
  ib_gateway_password_file: str | None = None
  ib_gateway_password_path: str = "~/.secrets/ibkr-gateway"
  application_port: int = 8000
  log_level: str = "INFO"
  mode: str = "PROD"

  # Non-essential parameters
  enable_file_logging: bool = False
  log_file_path: str = "logs/app.log"

  # IBKR Gateway parameters
  ib_gateway_persist: bool = False
  ib_gateway_host: str = "localhost"
  ib_gateway_vnc_port: int = 5900
  ib_gateway_port: int = 4002
  ib_command_server_port: int = 7462
  ib_gateway_tradingmode: str = "paper"
  ib_gateway_readonly: bool = True
  ib_gateway_vnc_password: str | None = None
  ib_gateway_vnc_password_file: str | None = None
  ib_gateway_image: str = "ghcr.io/gnzsnz/ib-gateway:latest"
  password_file: str | None = None
  tws_rdp_port: int = 3389
  mcp_transport: str = "streamable-http"

  # Timeout configuration (in seconds)
  ib_connection_timeout: int = 300
  ib_gateway_timeout: int = 300
  ib_request_timeout: int = 10


class ConfigManager:
  """Singleton class to manage the global config."""

  _instance: Config = None

  @classmethod
  def get_config(cls) -> Config:
    """Get the global config instance."""
    if cls._instance is None:
      cls._instance = Config()
    return cls._instance

  @classmethod
  def init_config(
    cls,
    ib_gateway_username: str,
    application_port: int,
    ib_gateway_password: str | None = None,
    ib_gateway_password_file: str | None = None,
    log_level: str = "INFO",
    mode: str = "PROD",
    ib_gateway_tradingmode: str = "paper",
    ib_gateway_readonly: bool = True,
    ib_gateway_vnc_password: str | None = None,
    ib_gateway_vnc_password_file: str | None = None,
    ib_gateway_image: str = "ghcr.io/gnzsnz/ib-gateway:latest",
    password_file: str | None = None,
    tws_rdp_port: int = 3389,
    mcp_transport: str = "streamable-http",
  ) -> Config:
    """Initialize the global config with CLI parameters.

    Args:
        ib_gateway_username: IBKR Gateway username
        ib_gateway_password: IBKR Gateway password
          (optional, for backward compatibility)
        ib_gateway_password_file: Host path to the password file
          (defaults to ~/.secrets/ibkr/<USERNAME>)
        application_port: Port to run the application on
        log_level: Logging level
        mode: Application mode (PROD/DEV)
        ib_gateway_tradingmode: Trading mode (paper/live)
        ib_gateway_readonly: IBKR Gateway read-only mode
        ib_gateway_vnc_password: VNC password to enable x11vnc
        ib_gateway_vnc_password_file: Host path to the VNC password file
          (defaults to ~/.secrets/ibkr-gateway/vnc_password)
        ib_gateway_image: Docker image for IBKR Gateway
        password_file: Host path to the abc password file
          (defaults to ~/.secrets/ibkr-gateway/abc_password)
        tws_rdp_port: Host port for container-side RDP (default: 3389)
        mcp_transport: MCP transport type (streamable-http or sse)

    """
    config_kwargs = {}

    config_kwargs["ib_gateway_username"] = ib_gateway_username
    if ib_gateway_password:
      config_kwargs["ib_gateway_password"] = ib_gateway_password
    if ib_gateway_password_file:
      config_kwargs["ib_gateway_password_file"] = ib_gateway_password_file
    config_kwargs["application_port"] = application_port
    config_kwargs["log_level"] = log_level
    config_kwargs["mode"] = mode
    config_kwargs["ib_gateway_tradingmode"] = ib_gateway_tradingmode
    config_kwargs["ib_gateway_readonly"] = ib_gateway_readonly
    if ib_gateway_vnc_password:
      config_kwargs["ib_gateway_vnc_password"] = ib_gateway_vnc_password
    if ib_gateway_vnc_password_file:
      config_kwargs["ib_gateway_vnc_password_file"] = ib_gateway_vnc_password_file
    config_kwargs["ib_gateway_image"] = ib_gateway_image
    if password_file:
      config_kwargs["password_file"] = password_file
    config_kwargs["tws_rdp_port"] = tws_rdp_port
    config_kwargs["mcp_transport"] = mcp_transport
    cls._instance = Config(**config_kwargs)
    return cls._instance


# Convenience functions
def get_config() -> Config:
  """Get the global config instance."""
  return ConfigManager.get_config()


def init_config(
  ib_gateway_username: str,
  application_port: int,
  ib_gateway_password: str | None = None,
  ib_gateway_password_file: str | None = None,
  log_level: str = "INFO",
  mode: str = "PROD",
  ib_gateway_tradingmode: str = "paper",
  ib_gateway_readonly: bool = True,
    ib_gateway_vnc_password: str | None = None,
    ib_gateway_vnc_password_file: str | None = None,
    ib_gateway_image: str = "ghcr.io/gnzsnz/ib-gateway:latest",
    password_file: str | None = None,
    tws_rdp_port: int = 3389,
    mcp_transport: str = "streamable-http",
) -> Config:
    """Initialize the global config with CLI parameters.

    Args:
        ib_gateway_username: IBKR Gateway username
        ib_gateway_password: IBKR Gateway password
        (optional, for backward compatibility)
        ib_gateway_password_file: Host path to the password file
        (defaults to ~/.secrets/ibkr/<USERNAME>)
        application_port: Port to run the application on
        log_level: Logging level
        mode: Application mode (PROD/DEV)
        ib_gateway_tradingmode: Trading mode (paper/live)
        ib_gateway_readonly: IBKR Gateway read-only mode
        ib_gateway_vnc_password: VNC password to enable x11vnc
        ib_gateway_vnc_password_file: Host path to the VNC password file
        (defaults to ~/.secrets/ibkr-gateway/vnc_password)
        ib_gateway_image: Docker image for IBKR Gateway
        password_file: Host path to the abc password file
        (defaults to ~/.secrets/ibkr-gateway/abc_password)
        tws_rdp_port: Host port for container-side RDP (default: 3389)
        mcp_transport: MCP transport type (streamable-http or sse)

    """
    return ConfigManager.init_config(
        ib_gateway_username=ib_gateway_username,
        ib_gateway_password=ib_gateway_password,
        ib_gateway_password_file=ib_gateway_password_file,
        application_port=application_port,
        log_level=log_level,
        mode=mode,
        ib_gateway_tradingmode=ib_gateway_tradingmode,
        ib_gateway_readonly=ib_gateway_readonly,
        ib_gateway_vnc_password=ib_gateway_vnc_password,
        ib_gateway_vnc_password_file=ib_gateway_vnc_password_file,
        ib_gateway_image=ib_gateway_image,
        password_file=password_file,
        tws_rdp_port=tws_rdp_port,
        mcp_transport=mcp_transport,
    )
