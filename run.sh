#!/bin/bash

# Install dependencies
uv sync --reinstall

# Run the IBKR MCP Server using uv
uv run python main.py \
  --ib-gateway-tradingmode=paper \
  --port "${IBKR_MCP_PORT:-8000}" \
  --ib-gateway-vnc-password "${IB_GATEWAY_VNC_PASSWORD:-ibkr-gateway}" \
  "$@"