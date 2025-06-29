"""Logging configuration for the IBKR Agent project."""

import sys
import logging
from loguru import logger
from app.core.config import get_config


def setup_logging() -> None:
  """Set up logging configuration based on settings."""
  config = get_config()

  # Remove default logger
  logger.remove()

  # Configure console logging
  log_level = config.log_level

  # Add console handler
  logger.add(
    sys.stdout,
    level=log_level,
    colorize=True,
  )

  # Add file handler if enabled
  if config.enable_file_logging and config.log_file_path:
    logger.add(
      config.log_file_path,
      level=log_level,
      rotation="10 MB",
      retention="7 days",
    )

  logging.getLogger("ib_async").setLevel(logging.CRITICAL)
  logging.getLogger("uvicorn").setLevel(logging.CRITICAL)
  logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)
  logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
  logging.getLogger("fastapi").setLevel(logging.CRITICAL)
  logging.getLogger("asyncio").setLevel(logging.CRITICAL)

  return logger


# Initialize logging
setup_logging()
