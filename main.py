"""Simple entry point for the IBKR MCP Server."""

import argparse
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from app.core.config import init_config

def parse_args() -> argparse.Namespace:
  """Parse command line arguments."""
  parser = argparse.ArgumentParser(description="IBKR MCP Server")
  parser.add_argument(
    "--port",
    type=int,
    default=8000,
    help="Application port (default: 8000)",
  )
  parser.add_argument(
    "--log-level",
    type=str,
    default="INFO",
    help="Log level (default: INFO)",
  )
  parser.add_argument(
    "--mode",
    type=str,
    choices=["PROD", "DEV"],
    default="PROD",
    help="Application mode - 'PROD' or 'DEV' (default: PROD)",
  )
  parser.add_argument(
    "--ib-gateway-tradingmode",
    type=str,
    choices=["paper", "live"],
    default="paper",
    help="IBKR Gateway trading mode - 'paper' or 'live' (default: paper)",
  )
  return parser.parse_args()

def load_environment():
  """Load environment variables from .env file."""
  env_path = Path('.') / '.env'
  load_dotenv(dotenv_path=env_path)
  
  # Required environment variables
  required_vars = ['IB_GATEWAY_USERNAME', 'IB_GATEWAY_PASSWORD']
  missing_vars = [var for var in required_vars if not os.getenv(var)]
  
  if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
  
  return os.environ

def main() -> None:
  """Run the app."""
  # Load environment variables first
  env = load_environment()
  args = parse_args()

  # Initialize global config with environment variables and CLI parameters
  config = init_config(
    application_port=args.port,
    ib_gateway_username=env['IB_GATEWAY_USERNAME'],
    ib_gateway_password=env['IB_GATEWAY_PASSWORD'],
    log_level=args.log_level,
    mode=args.mode,
    ib_gateway_tradingmode=args.ib_gateway_tradingmode,
  )

  from app.main import app # noqa: PLC0415
  uvicorn.run(
    app,
    host="127.0.0.1",
    port=config.application_port,
    log_level="critical",
    access_log=False,
  )

if __name__ == "__main__":
  main()
