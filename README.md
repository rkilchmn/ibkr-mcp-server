# IBKR MCP Server

A FastAPI application that provides an MCP (Model Context Protocol) server for Interactive Brokers (IBKR) trading operations. The server automatically manages an IBKR Gateway Docker container and exposes trading functionality through both REST API and MCP endpoints.

## Features

- **Docker Management**: Automatic IBKR Gateway container lifecycle
- **Account Management**: Account summary, positions, and account values
- **Trading Operations**: Place orders, cancel orders, manage open orders
- **Market Data**: Real-time snapshots, historical data, tickers, options chains
- **Contract Management**: Contract details, options chains, scanners
- **Connection Management**: Connection status and reconnection
- **MCP Integration**: All API endpoints automatically exposed as MCP tools via FastMCP
- **Health Monitoring**: Health checks, restarts gateways when no market data

## Quick Start

### Prerequisites

- Python 3.13+
- Docker installed and running
- IBKR account credentials

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd ibkr-mcp-server
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Run the server:**
   ```bash
   python main.py --ib-gateway-username=$YOUR_USERNAME --ib-gateway-password=$YOUR_PASSWORD
   ```

The server will start on `http://localhost:8000` with API docs at `/docs`. MCP server will be available at `http://localhost:8000/mcp`.

## API Endpoints

All IBKR endpoints are automatically exposed as MCP tools via FastMCP.

### Gateway Management
These are not exposed to MCP by default
- `GET /gateway/status` - Gateway health and status
- `GET /gateway/logs` - Container logs

### Account Management
- `GET /ibkr/account/summary` - Get account summary information
- `GET /ibkr/account/values` - Get all account values
- `GET /ibkr/account/positions` - Get detailed position information with P&L

### Trading Operations
- `POST /ibkr/orders/place` - Place a trading order (market, limit, stop, etc.)
- `DELETE /ibkr/orders/{order_id}` - Cancel an order by ID
- `GET /ibkr/orders/open` - Get all open orders

### Market Data
- `GET /ibkr/tickers` - Market data tickers for contract IDs
- `GET /ibkr/market_data/historical` - Get historical OHLCV bar data
- `GET /ibkr/market_data/snapshot` - Get real-time market data snapshot
- `GET /ibkr/filtered_options_chain` - Filtered options chain with market data criteria

### Contract Management
- `GET /ibkr/positions` - Current positions (simple)
- `GET /ibkr/contract_details` - Contract information for a symbol
- `GET /ibkr/options_chain` - Options chain for underlying contracts

### Scanner Operations
- `GET /ibkr/scanner/instrument_codes` - Available scanner instrument codes
- `GET /ibkr/scanner/location_codes` - Available scanner location codes
- `GET /ibkr/scanner/filter_codes` - Available scanner filter codes
- `GET /ibkr/scanner/results` - Scanner results with specified parameters

### Connection Management
- `GET /ibkr/connection/status` - Get current connection status
- `POST /ibkr/connection/reconnect` - Reconnect to IBKR Gateway/TWS

## Troubleshooting

- **Docker issues**: Ensure Docker daemon is running
- **Port conflicts**: Check if port 8000 is available
- **IBKR connection**: Verify credentials and TWS/Gateway setup

## License

MIT License
