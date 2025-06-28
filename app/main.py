"""Main module for the IBKR MCP Server."""

from fastapi import FastAPI
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.api.endpoints import gateway

from app.core.config import get_config
from app.core.setup_logging import setup_logging

config = get_config()
logger = setup_logging()

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
  """Lifespan events for the application."""
  logger.info("Starting IBKR MCP Server...")
  try:
    success = await gateway.gateway_manager.start_gateway()
    if success:
      logger.info("IBKR Gateway started successfully!")
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


@app.get("/")
def read_root() -> dict:
  """Read the root endpoint."""
  return {
    "message": "Welcome to the IBKR MCP Server",
    "docs": "/docs",
    "gateway_endpoints": "/gateway",
  }

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(
    app,
    host="127.0.0.1",
    port=config.application_port,
  )
