"""Configuration for the application."""
from pydantic_settings import BaseSettings

class Config(BaseSettings):
  """Global configuration for the application."""

  ib_gateway_username: str
  ib_gateway_password: str
  application_port: int = 8000
  log_level: str = "INFO"
  mode: str = "PROD"

  # Non-essential parameters
  enable_file_logging: bool = False
  log_file_path: str = "logs/app.log"

  # IBKR Gateway parameters
  ib_gateway_persist: bool = False
  ib_gateway_host: str = "localhost"
  ib_gateway_port: int = 8888
  ib_command_server_port: int = 7462
  ib_gateway_tradingmode: str = "paper"


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
    ib_gateway_password: str,
    application_port: int,
    log_level: str = "INFO",
    mode: str = "PROD",
    ib_gateway_tradingmode: str = "paper",
  ) -> Config:
    """Initialize the global config with CLI parameters.
    
    Args:
        ib_gateway_username: IBKR Gateway username
        ib_gateway_password: IBKR Gateway password
        application_port: Port to run the application on
        log_level: Logging level
        mode: Application mode (PROD/DEV)
        ib_gateway_tradingmode: Trading mode (paper/live)
    """
    config_kwargs = {}

    config_kwargs["ib_gateway_username"] = ib_gateway_username
    config_kwargs["ib_gateway_password"] = ib_gateway_password
    config_kwargs["application_port"] = application_port
    config_kwargs["log_level"] = log_level
    config_kwargs["mode"] = mode
    config_kwargs["ib_gateway_tradingmode"] = ib_gateway_tradingmode
    cls._instance = Config(**config_kwargs)
    return cls._instance

# Convenience functions
def get_config() -> Config:
  """Get the global config instance."""
  return ConfigManager.get_config()

def init_config(
  ib_gateway_username: str,
  ib_gateway_password: str,
  application_port: int,
  log_level: str = "INFO",
  mode: str = "PROD",
  ib_gateway_tradingmode: str = "paper",
) -> Config:
  """Initialize the global config with CLI parameters.
  
  Args:
      ib_gateway_username: IBKR Gateway username
      ib_gateway_password: IBKR Gateway password
      application_port: Port to run the application on
      log_level: Logging level
      mode: Application mode (PROD/DEV)
      ib_gateway_tradingmode: Trading mode (paper/live)
  """
  return ConfigManager.init_config(
    ib_gateway_username=ib_gateway_username,
    ib_gateway_password=ib_gateway_password,
    application_port=application_port,
    log_level=log_level,
    mode=mode,
    ib_gateway_tradingmode=ib_gateway_tradingmode,
  )
