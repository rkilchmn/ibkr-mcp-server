"""Main module for the IBKR MCP Server."""

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.api import gateway
from app.api.ibkr import ibkr_router
from app.core.setup_logging import setup_logging

logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
  """Lifespan events for the application."""
  port = getattr(app.state, 'port', 8000)
  logger.info(f"Starting IBKR API/MCP Server on port {port}...")
  try:
    success = await gateway.gateway_manager.start_gateway()
    if success:
      logger.info("IBKR Gateway started successfully!")
      from app.core.config import get_config
      cfg = get_config()
      logger.info(
        f"IBKR Gateway tradingmode={cfg.ib_gateway_tradingmode} "
        f"(change with --ib-gateway-tradingmode=live)"
      )
      logger.info(
        f"IBKR Gateway readonly={cfg.ib_gateway_readonly} "
        f"(change with --ib-gateway-readonly=false)"
      )
      logger.info(
        f"MCP transport={cfg.mcp_transport} "
        f"(change with --mcp-transport=sse)"
      )
      if cfg.mcp_transport == "streamable-http":
        mcp.mount_http()
      else:
        mcp.mount_sse()
    else:
      logger.error("Failed to start IBKR Gateway.")
  except Exception:
    logger.exception("Error starting IBKR Gateway.")

  yield

  # Shutdown
  logger.info("Shutting down IBKR MCP Server...")

  # Cleanup gateway
  try:
    await gateway.gateway_manager.cleanup()
  except Exception:
    logger.exception("Error during cleanup.")


app = FastAPI(
  title="IBKR MCP Server",
  description="Interactive Brokers MCP Server",
  version="1.0.0",
  docs_url="/docs",
  lifespan=lifespan,
)

# Include routers
app.include_router(gateway.router)
app.include_router(ibkr_router)

@app.get("/", tags=["root"])
def read_root() -> dict:
  """Return the root endpoint."""
  return {
    "message": "Welcome to the IBKR MCP Server",
    "docs": "/docs",
    "gateway_endpoints": "/gateway",
  }

# MCP server, attached to the FastAPI app
mcp = FastApiMCP(app, exclude_tags=["root"])

# Patch MCP tool schemas to accept dicts for filters/criteria instead of strings
for tool in mcp.tools:
    if tool.name in ("get_options_chain", "get_filtered_options_chain"):
        props = tool.inputSchema.get("properties", {})
        if "filters" in props:
            props["filters"] = {
                "anyOf": [
                    {"type": "object"},
                    {"type": "null"},
                ],
                "description": "Filters as a dict (e.g., {'trading_class': ['SPXW'], 'expirations': ['20250505'], 'strikes': [5490], 'rights': ['C']})",
                "title": "filters",
            }
        if "criteria" in props:
            props["criteria"] = {
                "anyOf": [
                    {"type": "object"},
                    {"type": "null"},
                ],
                "description": "Criteria as a dict (e.g., {'min_delta': -0.06, 'max_delta': -0.04})",
                "title": "criteria",
            }
    if tool.name == "get_market_data":
        props = tool.inputSchema.get("properties", {})
        if "contract_ids" in props:
            props["contract_ids"] = {
                "anyOf": [
                    {"type": "array", "items": {"type": "integer"}},
                    {"type": "integer"},
                    {"type": "null"},
                ],
                "description": "One or more contract IDs. Pass a single int or a list of ints.",
                "title": "contract_ids",
            }
