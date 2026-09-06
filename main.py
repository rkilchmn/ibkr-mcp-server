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
    "--mcp-port",
    type=int,
    default=None,
    help="MCP application port (default: 8000, or MCP_PORT env var)",
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
    "--read-only-api",
    type=lambda x: x.lower() == "true",
    default=None,
    help="IBKR Gateway read-only API mode - 'true' or 'false' (default: true)",
  )
  parser.add_argument(
    "--ib-gateway-vnc-password",
    type=str,
    default=None,
    help="VNC password to enable x11vnc inside the gateway container",
  )
  parser.add_argument(
    "--ib-gateway-image",
    type=str,
    default=None,
    help="Docker image for IBKR Gateway (default: ghcr.io/gnzsnz/ib-gateway:latest)",
  )
  parser.add_argument(
    "--tws-rdp-port",
    type=int,
    default=None,
    help="Host port for container-side RDP (default: 3389)",
  )
  parser.add_argument(
    "--ib-gateway-data-path",
    type=str,
    default=None,
    help="Base directory for config/ and .docker/ (default: ib-gateway-data in current dir, or IB_GATEWAY_DATA_PATH env var)",
  )
  parser.add_argument(
    "--ib-gateway-tws-settings-path",
    type=str,
    default=None,
    help="Host path for TWS settings persistence "
    "(default: ./tws_settings for ib-gateway, ./config for tws-rdesktop)",
  )
  parser.add_argument(
    "--ib-gateway-credentials-path",
    type=str,
    default=None,
    help="Host path for credential files (default: ~/.secrets/ib-gateway, or IB_GATEWAY_CREDENTIALS_PATH env var)",
  )
  parser.add_argument(
    "--password-file",
    type=str,
    default=None,
    help="Host path to the abc password file "
    "(default: ~/.secrets/ibkr-gateway/abc_password)",
  )
  parser.add_argument(
    "--vnc-password-file",
    type=str,
    default=None,
    help="Host path to the VNC password file "
    "(default: ~/.secrets/ibkr-gateway/vnc_password)",
  )
  parser.add_argument(
    "--mcp-transport",
    type=str,
    choices=["streamable-http", "sse"],
    default="streamable-http",
    help="MCP transport type - 'streamable-http' or 'sse' (default: streamable-http)",
  )
  parser.add_argument(
    "--ib-gateway-username",
    type=str,
    default=None,
    help="IBKR Gateway username (overrides IB_GATEWAY_USERNAME env var)",
  )
  parser.add_argument(
    "--env-file",
    type=str,
    default=None,
    help="Path to the .env file (default: ./.env, or ENV_FILE env var)",
  )
  return parser.parse_args()


def load_environment(env_file_path: str | None = None):
  """Load environment variables from .env file."""
  path = env_file_path or ".env"
  env_path = Path(path)
  if env_path.exists():
    load_dotenv(dotenv_path=env_path)

  return os.environ


def main() -> None:
  """Run the app."""
  args = parse_args()
  env_file = args.env_file or os.getenv("ENV_FILE") or ".env"
  env = load_environment(env_file)

  username = args.ib_gateway_username or env["IB_GATEWAY_USERNAME"]
  # Derive password file path from username if not explicitly set
  credentials_path = args.ib_gateway_credentials_path or env.get("IB_GATEWAY_CREDENTIALS_PATH")
  data_path = args.ib_gateway_data_path or env.get("IB_GATEWAY_DATA_PATH")
  password_file = env.get("IB_GATEWAY_PASSWORD_FILE")
  if not password_file:
    password_file = f"~/.secrets/ib-gateway/{username}"

  # Initialize global config with environment variables and CLI parameters
  config = init_config(
    application_port=args.mcp_port
    or int(env.get("MCP_PORT", "8000")),
    ib_gateway_username=username,
    ib_gateway_password=env.get("IB_GATEWAY_PASSWORD"),
    ib_gateway_password_file=password_file,
    log_level=args.log_level,
    mode=args.mode,
    ib_gateway_tradingmode=args.ib_gateway_tradingmode,
    ib_gateway_readonly=args.read_only_api
    if args.read_only_api is not None
    else env.get("READ_ONLY_API", "true").lower() == "true",
    ib_gateway_vnc_password=args.ib_gateway_vnc_password
    or env.get("IB_GATEWAY_VNC_PASSWORD"),
    ib_gateway_vnc_password_file=args.vnc_password_file or env.get("VNC_PASSWORD_FILE"),
    ib_gateway_image=args.ib_gateway_image or env.get("IB_GATEWAY_IMAGE"),
    ib_gateway_credentials_path=credentials_path,
    ib_gateway_data_path=data_path,
    password_file=args.password_file or env.get("PASSWORD_FILE"),
    tws_rdp_port=args.tws_rdp_port
    if args.tws_rdp_port
    else int(env.get("TWS_RDP_PORT", "3389")),
    ib_gateway_tws_settings_path=args.ib_gateway_tws_settings_path
    or env.get("IB_GATEWAY_TWS_SETTINGS_PATH"),
    mcp_transport=args.mcp_transport,
  )

  from app.main import app  # noqa: PLC0415

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
