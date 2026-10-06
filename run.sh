#!/bin/bash

# Install dependencies
uv sync --reinstall

# Run the IBKR MCP Server using uv
uv run python main.py \
  --ib-gateway-tradingmode=paper \
  --read-only-api=false \
  --mcp-port "${IBKR_MCP_PORT:-8002}" \
  --ib-gateway-docker-image="ghcr.io/gnzsnz/tws-rdesktop:latest" \
  "$@"