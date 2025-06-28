"""Main module for the IBKR MCP Server."""

import logging
from fastapi import FastAPI
from app.api.endpoints import portfolio, gateway
from app.core.config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = get_config()
logger.info(f"Config: {config}")

app = FastAPI(
  title="IBKR MCP Server",
  description="Interactive Brokers MCP Server with Docker Gateway Management",
  version="1.0.0",
  docs_url="/docs",
)

# Include routers
app.include_router(portfolio.router)
app.include_router(gateway.router)


@app.get("/")
def read_root() -> dict:
  """Read the root endpoint."""
  return {
    "message": "Welcome to the IBKR MCP Server",
    "docs": "/docs",
    "gateway_endpoints": "/gateway",
  }


@app.on_event("startup")
async def startup_event():
  """Initialize the application on startup."""
  logger.info("Starting IBKR MCP Server...")

  # Automatically start the IBKR Gateway
  try:
    logger.info("Starting IBKR Gateway container automatically...")
    success = await gateway.gateway_manager.start_gateway()
    if success:
      logger.info("IBKR Gateway started successfully!")
    else:
      logger.error("Failed to start IBKR Gateway")
  except Exception as e:
    logger.error(f"Error starting IBKR Gateway: {e}")


@app.on_event("shutdown")
async def shutdown_event():
  """Cleanup on application shutdown."""
  logger.info("Shutting down IBKR MCP Server...")

  # Cleanup gateway
  try:
    await gateway.gateway_manager.cleanup()
  except Exception as e:
    logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
  import uvicorn
  uvicorn.run(
    app,
    host="127.0.0.1",
    port=config.application_port,
  )
