"""Configuration for the application."""
from pydantic_settings import BaseSettings

class Config(BaseSettings):
  """Global configuration for the application."""

  ibkr_gateway_username: str
  ibkr_gateway_password: str
  application_port: int = 8000

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
    ibkr_gateway_username: str,
    ibkr_gateway_password: str,
    application_port: int,
  ) -> Config:
    """Initialize the global config with CLI parameters."""
    config_kwargs = {}

    config_kwargs["ibkr_gateway_username"] = ibkr_gateway_username
    config_kwargs["ibkr_gateway_password"] = ibkr_gateway_password
    config_kwargs["application_port"] = application_port

    cls._instance = Config(**config_kwargs)
    return cls._instance

# Convenience functions
def get_config() -> Config:
  """Get the global config instance."""
  return ConfigManager.get_config()

def init_config(
  ibkr_gateway_username: str,
  ibkr_gateway_password: str,
  application_port: int,
) -> Config:
  """Initialize the global config with CLI parameters."""
  return ConfigManager.init_config(
    ibkr_gateway_username=ibkr_gateway_username,
    ibkr_gateway_password=ibkr_gateway_password,
    application_port=application_port,
  )
