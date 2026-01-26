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

4. ** Troubleshoot **

You can use http://localhost:6080/ for browser based VLC

## API Documentation

All IBKR endpoints are automatically exposed as MCP tools via FastMCP. The API follows RESTful conventions and returns JSON responses.

### Gateway Management

These endpoints provide information about the IBKR Gateway Docker container.

#### `GET /gateway/status`
Get the current status of the IBKR Gateway container.

**Example:**
```bash
curl -X GET "http://localhost:8000/gateway/status"
```

**Response:**
```json
{
  "status": "running",
  "container_id": "a1b2c3d4e5f6",
  "started_at": "2025-10-05T10:00:00Z"
}
```

#### `GET /gateway/logs`
Retrieve the container logs (last 100 lines by default).

**Query Parameters:**
- `tail`: Number of log lines to return (default: 100)

**Example:**
```bash
curl -X GET "http://localhost:8000/gateway/logs?tail=100"
```

---


### Account Management

#### `GET /ibkr/account/summary`
Get a summary of the trading account information.

**Query Parameters:**
- `account_id`: (Optional) Specific account ID. If not provided, uses the default account.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/account/summary"
```

**Response:**
```json
{
  "account_id": "DU1234567",
  "account_type": "INDIVIDUAL",
  "net_liquidation_value": 125000.50,
  "total_cash_value": 25000.75,
  "gross_position_value": 100000.25,
  "unrealized_pnl": 2500.00,
  "realized_pnl": 1500.50,
  "available_funds": 50000.25,
  "excess_liquidity": 52000.75,
  "buying_power": 150000.00,
  "leverage": 1.5
}
```

#### `GET /ibkr/account/positions`
Get detailed information about current positions.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/account/positions"
```

**Response:**
```json
[
  {
    "contract_id": 12345678,
    "symbol": "AAPL",
    "position": 100,
    "average_cost": 150.25,
    "market_price": 155.75,
    "market_value": 15575.00,
    "unrealized_pnl": 550.00,
    "realized_pnl": 0.00,
    "asset_class": "STK",
    "expiry": null,
    "strike": null,
    "right": null,
    "multiplier": 1.0
  }
]
```

### Trading Operations

#### `POST /ibkr/orders/place`
Place a new order.

**Request Body:**
```json
{
  "contract_id": 12345678,
  "order_type": "LMT",
  "action": "BUY",
  "quantity": 10,
  "limit_price": 150.25,
  "time_in_force": "DAY",
  "tif": "20241231 23:59:59",
  "outside_rth": false,
  "transmit": true
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/ibkr/orders/place" \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": 12345678,
    "order_type": "LMT",
    "action": "BUY",
    "quantity": 10,
    "limit_price": 150.25,
    "time_in_force": "DAY",
    "tif": "20241231 23:59:59",
    "outside_rth": false,
    "transmit": true
  }'
```

**Response:**
```json
{
  "order_id": 987654321,
  "status": "Submitted",
  "filled_quantity": 0,
  "remaining_quantity": 10,
  "average_fill_price": 0.0,
  "last_fill_price": 0.0,
  "error_message": null
}
```

#### `DELETE /ibkr/orders/{order_id}`
Cancel an existing order.

**Path Parameters:**
- `order_id`: The ID of the order to cancel

**Example:**
```bash
curl -X DELETE "http://localhost:8000/ibkr/orders/987654321"
```

**Response:**
```json
{
  "order_id": 987654321,
  "status": "Cancelled",
  "message": "Order cancelled successfully"
}
```

### Market Data

#### `GET /ibkr/market_data/snapshot`
Get real-time market data snapshot for a contract.

**Query Parameters:**
- `contract_id`: The IBKR contract ID
- `symbol`: Symbol (alternative to contract_id)
- `sec_type`: Security type (e.g., STK, OPT, FUT)
- `exchange`: Exchange (e.g., SMART, ISLAND)
- `currency`: Currency (e.g., USD)

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/market_data/snapshot?contract_id=12345678"
```

**Response:**
```json
{
  "symbol": "AAPL",
  "last_price": 155.75,
  "bid": 155.70,
  "ask": 155.80,
  "bid_size": 5,
  "ask_size": 3,
  "volume": 1250000,
  "open": 154.25,
  "high": 156.10,
  "low": 153.90,
  "close": 154.50,
  "timestamp": "2025-10-05T10:15:30Z"
}
```

#### `GET /ibkr/market_data/historical`
Get historical market data.

**Query Parameters:**
- `contract_id`: The IBKR contract ID
- `duration`: Data duration (e.g., "1 D", "1 W", "1 M", "1 Y")
- `bar_size`: Bar size (e.g., "1 min", "5 mins", "1 hour", "1 day")
- `what_to_show`: Data type (e.g., "TRADES", "MIDPOINT", "BID", "ASK")
- `use_rth`: Use regular trading hours only (true/false)

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/market_data/historical?contract_id=12345678&duration=1%20D&bar_size=1%20min&what_to_show=TRADES&use_rth=true"
```

**Response:**
```json
{
  "symbol": "AAPL",
  "bars": [
    {
      "time": "2025-10-05T09:30:00-04:00",
      "open": 155.25,
      "high": 155.40,
      "low": 155.10,
      "close": 155.30,
      "volume": 2500,
      "count": 125,
      "wap": 155.25
    },
    {
      "time": "2025-10-05T09:35:00-04:00",
      "open": 155.30,
      "high": 155.75,
      "low": 155.25,
      "close": 155.70,
      "volume": 3200,
      "count": 150,
      "wap": 155.50
    }
  ]
}
```

### Contract Management

#### `GET /ibkr/contract_details`
Get detailed information about a contract.

**Query Parameters:**
- `symbol`: The symbol (e.g., AAPL)
- `sec_type`: Security type (e.g., STK, OPT, FUT)
- `exchange`: Exchange (e.g., SMART, ISLAND)
- `currency`: Currency (e.g., USD)
- `expiry`: Expiration date (YYYYMM or YYYYMMDD for options/futures)
- `strike`: Strike price (for options)
- `right`: Put or Call (for options)

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/contract_details?symbol=AAPL&sec_type=STK&exchange=SMART&currency=USD"
```

**Response:**
```json
{
  "contract_id": 12345678,
  "symbol": "AAPL",
  "sec_type": "STK",
  "exchange": "SMART",
  "primary_exchange": "NASDAQ",
  "currency": "USD",
  "trading_class": "NMS",
  "conid": 12345678,
  "multiplier": 1.0,
  "min_tick": 0.01,
  "price_magnifier": 1,
  "last_trade_date": "",
  "strike": 0.0,
  "right": "",
  "expiry": "",
  "industry": "Technology",
  "category": "Computers",
  "subcategory": "Computer Hardware"
}
```

### Scanner Operations

#### `GET /ibkr/scanner/results`
Run a market scanner with specified parameters.

**Query Parameters:**
- `instrument`: Instrument type (e.g., "STK", "FUT", "OPT")
- `location_code`: Location code (e.g., "STK.US.MAJOR")
- `filter_codes`: Comma-separated filter codes (e.g., "priceAbove5,volume_avg_1000")
- `above_price`: Filter for price above
- `below_price`: Filter for price below
- `above_volume`: Filter for volume above
- `market_cap_above`: Filter for market cap above
- `market_cap_below`: Filter for market cap below

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/results?instrument=STK&location_code=STK.US.MAJOR"
```

**Response:**
```json
{
  "scan_results": [
    {
      "contract_id": 12345678,
      "symbol": "AAPL",
      "sec_type": "STK",
      "exchange": "SMART",
      "last_price": 155.75,
      "change_percent": 0.81,
      "volume": 1250000,
      "market_cap": 2500000000000,
      "pe_ratio": 28.5,
      "sector": "Technology"
    },
    {
      "contract_id": 23456789,
      "symbol": "MSFT",
      "sec_type": "STK",
      "exchange": "SMART",
      "last_price": 330.25,
      "change_percent": 0.45,
      "volume": 980000,
      "market_cap": 2450000000000,
      "pe_ratio": 32.1,
      "sector": "Technology"
    }
  ],
  "scan_time": "2025-10-05T10:20:15Z"
}
```

### Connection Management

#### `GET /ibkr/connection/status`
Get the current connection status to IBKR Gateway/TWS.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/connection/status"
```

**Response:**
```json
{
  "connected": true,
  "client_id": 0,
  "server_version": "10.19",
  "connection_time": "2025-10-05T09:00:00Z",
  "connection_status": "Connected",
  "connection_status_message": "TWS Connection OK"
}
```

#### `POST /ibkr/connection/reconnect`
Reconnect to IBKR Gateway/TWS.

**Example:**
```bash
curl -X POST "http://localhost:8000/ibkr/connection/reconnect"
```

**Response:**
```json
{
  "success": true,
  "message": "Reconnection initiated",
  "timestamp": "2025-10-05T10:25:00Z"
}
```

## Troubleshooting

- **Docker issues**: Ensure Docker daemon is running
- **Port conflicts**: Check if port 8000 is available
- **IBKR connection**: Verify credentials and TWS/Gateway setup

## License

MIT License
