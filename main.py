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
  parser.add_argument(
    "--ib-gateway-readonly",
    type=lambda x: x.lower() == "true",
    default=True,
    help="IBKR Gateway read-only mode - 'true' or 'false' (default: true)",
  )
  parser.add_argument(
    "--ib-gateway-vnc-password",
    type=str,
    default=None,
    help="VNC password to enable x11vnc inside the gateway container",
  )
  parser.add_argument(
    "--mcp-transport",
    type=str,
    choices=["streamable-http", "sse"],
    default="streamable-http",
    help="MCP transport type - 'streamable-http' or 'sse' (default: streamable-http)",
  )
  return parser.parse_args()

def load_environment():
  """Load environment variables from .env file."""
  env_path = Path('.') / '.env'
  load_dotenv(dotenv_path=env_path)
  
  # Required environment variables
  required_vars = ['IB_GATEWAY_USERNAME']
  missing_vars = [var for var in required_vars if not os.getenv(var)]
  
  if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
  
  return os.environ

def main() -> None:
  """Run the app."""
  # Load environment variables first
  env = load_environment()
  args = parse_args()

  username = env["IB_GATEWAY_USERNAME"]
  # Derive password file path from username if not explicitly set
  password_file = env.get("IB_GATEWAY_PASSWORD_FILE")
  if not password_file:
    password_file = f"~/.secrets/ibkr/{username}"

  # Initialize global config with environment variables and CLI parameters
  config = init_config(
    application_port=args.port,
    ib_gateway_username=username,
    ib_gateway_password=env.get("IB_GATEWAY_PASSWORD"),
    ib_gateway_password_file=password_file,
    log_level=args.log_level,
    mode=args.mode,
    ib_gateway_tradingmode=args.ib_gateway_tradingmode,
    ib_gateway_readonly=args.ib_gateway_readonly,
    ib_gateway_vnc_password=args.ib_gateway_vnc_password or env.get("IB_GATEWAY_VNC_PASSWORD"),
    mcp_transport=args.mcp_transport,
  )

  from app.main import app # noqa: PLC0415
  app.state.port = config.application_port
  uvicorn.run(
    app,
    host="127.0.0.1",
    port=config.application_port,
    log_level="critical",
    access_log=False,
  )

if __name__ == "__main__":
  main()
