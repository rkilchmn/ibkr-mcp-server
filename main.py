"""Simple entry point for the IBKR MCP Server."""

import argparse
import uvicorn

from app.core.config import init_config

def parse_args() -> argparse.Namespace:
  """Parse command line arguments."""
  parser = argparse.ArgumentParser(description="IBKR MCP Server")
  parser.add_argument(
    "--ib-gateway-username",
    required=True,
    help="IBKR Gateway username",
  )
  parser.add_argument(
    "--ib-gateway-password",
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
    ib_gateway_username=args.ib_gateway_username,
    ib_gateway_password=args.ib_gateway_password,
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
