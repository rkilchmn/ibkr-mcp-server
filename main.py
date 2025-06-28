"""Simple entry point for the IBKR MCP Server."""

import argparse
import logging
import uvicorn

from app.main import app
from app.core.config import init_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
  """Parse command line arguments."""
  parser = argparse.ArgumentParser(description="IBKR MCP Server")
  parser.add_argument(
    "--ibkr-gateway-username",
    required=True,
    help="IBKR Gateway username",
  )
  parser.add_argument(
    "--ibkr-gateway-password",
    required=True,
    help="IBKR Gateway password",
  )
  parser.add_argument(
    "--port",
    type=int,
    default=8000,
    help="Application port (default: 8000)",
  )
  return parser.parse_args()

def main() -> None:
  """Run the app."""
  args = parse_args()

  # Initialize global config with CLI parameters
  config = init_config(
    application_port=args.port,
    ibkr_gateway_username=args.ibkr_gateway_username,
    ibkr_gateway_password=args.ibkr_gateway_password,
  )

  uvicorn.run(
    app,
    host="127.0.0.1",
    port=config.application_port,
  )

if __name__ == "__main__":
  main()
