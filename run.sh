#!/bin/bash

# Install dependencies
uv sync --reinstall

# Run the IBKR MCP Server using uv
uv run python main.py --ib-gateway-tradingmode=paper