# IBKR MCP Server

A FastAPI application that provides an MCP (Model Context Protocol) server for Interactive Brokers (IBKR) trading operations. The server automatically manages an IBKR Gateway Docker container and exposes trading functionality through both REST API and MCP endpoints.

## Features

- **Docker Management**: Automatic IBKR Gateway container lifecycle
- **Account Management**: Account summary, positions, and account values
- **Trading Operations**: Place orders, cancel orders, manage open orders
- **Market Data**: Real-time market data, historical data, options chains
- **Contract Management**: Contract details, options chains, scanners
- **Connection Management**: Connection status and reconnection
- **MCP Integration**: All API endpoints automatically exposed as MCP tools via FastMCP
- **Health Monitoring**: Health checks, restarts gateways when no market data

## Quick Start

### Prerequisites

- Python 3.13+
- Docker installed and running
- IBKR account credentials (username + password)

### Credentials Setup

The MCP server reads the IBKR Gateway password from a **host file** that is bind-mounted into the Gateway container at `/run/secrets/tws_password`. The MCP process does **not** read this file — only Docker and the container do. The file must be readable by the container's runtime user (uid `911` / group `911` inside the `ghcr.io/gnzsnz/ib-gateway` image).

**Recommended setup (default):**

```bash
# Default path is ~/.secrets/ibkr-gateway/<IB_GATEWAY_USERNAME>
sudo install -d -m 0700 -o root -g root ~/.secrets/ibkr-gateway
sudo sh -c 'umask 0177; echo "YOUR_IBKR_PASSWORD" > ~/.secrets/ibkr-gateway/ebljlc158'
sudo chown root:911 ~/.secrets/ibkr-gateway/ebljlc158
sudo chmod 0440 ~/.secrets/ibkr-gateway/ebljlc158
```

This creates a file owned by `root:911` with mode `0440` — readable by the container's uid/gid (`abc`), unreadable by other host users. The MCP server bind-mounts it directly into the container; no temporary copies are made.

**Custom secrets directory:** set `IB_GATEWAY_PASSWORD_PATH` in `.env` to override the default `~/.secrets/ibkr-gateway/`. The MCP server constructs the secret file path as `<IB_GATEWAY_PASSWORD_PATH>/<IB_GATEWAY_USERNAME>`:

```bash
IB_GATEWAY_PASSWORD_PATH=/secure/secrets   # looks for /secure/secrets/ebljlc158
```

**Custom file path:** set `IB_GATEWAY_PASSWORD_FILE` to use an explicit full path (no username suffix). This takes precedence over `IB_GATEWAY_PASSWORD_PATH`:

```bash
IB_GATEWAY_PASSWORD_FILE=/secure/path/tws_password
```

**Optional abc_password file:** set `PASSWORD_FILE` to specify a host path to an additional secret file that will be bind-mounted into the container at `/run/secrets/abc_password` (exposed as `PASSWD_FILE` env var inside the container). Default: `~/.secrets/ibkr-gateway/abc_password` (or `<IB_GATEWAY_PASSWORD_PATH>/abc_password` if that's set):

```bash
PASSWORD_FILE=/secure/path/abc_password
```

The same permission requirements apply: the file must be readable by the container's uid/gid (`911`). Modes that work include `0440` (group-readable), `0604` (world-readable, no group/other write), or `0644`.

**Security notes:**

- The password file is the only secret the container needs. Never bake it into a Docker image or commit it to source control.
- The container only sees the file at `/run/secrets/tws_password` (read-only bind mount). It cannot modify it.
- If you previously used the `IB_GATEWAY_PASSWORD` env var directly, that still works but is less secure (visible in `docker inspect`).

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
    ./run.sh
    ```
    
    Or manually:
    ```bash
    uv run python main.py --ib-gateway-tradingmode=paper
    ```
    
    Credentials are loaded from the `.env` file.

The server will start on `http://localhost:8000` with API docs at `/docs`. MCP server will be available at `http://localhost:8000/mcp`.

4. ** Troubleshoot **

You can use http://localhost:6080/ for browser based VNC

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
    "account": "DU123456",
    "symbol": "AAPL",
    "sec_type": "STK",
    "exchange": "NASDAQ",
    "currency": "USD",
    "position": 100.0,
    "avg_cost": 150.25,
    "market_price": 155.50,
    "market_value": 15550.00,
    "unrealized_pnl": 525.00,
    "realized_pnl": null,
    "contract_id": 265598
  }
]
```

#### `GET /ibkr/account/values`
Get all account values.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/account/values"
```

**Response:**
```json
[
  {
    "account": "DU123456",
    "key": "CashBalance",
    "value": "50000.00",
    "currency": "USD"
  }
]
```

### Trading Operations

#### `POST /ibkr/orders/place`
Place a new order.

**Request Body:**
```json
{
  "contract": {
    "con_id": 12345678
  },
  "order": {
    "action": "BUY",
    "total_quantity": 10,
    "order_type": "LMT",
    "lmt_price": 150.25,
    "time_in_force": "DAY"
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/ibkr/orders/place" \
  -H "Content-Type: application/json" \
  -d '{
    "contract": {
      "con_id": 12345678
    },
    "order": {
      "action": "BUY",
      "total_quantity": 10,
      "order_type": "LMT",
      "lmt_price": 150.25,
      "time_in_force": "DAY"
    }
  }'
```

**Response:**
```json
{
  "order_id": 987654321,
  "status": "Submitted",
  "symbol": "AAPL",
  "action": "BUY",
  "quantity": 10.0,
  "filled": 0.0,
  "remaining": 10.0,
  "avg_fill_price": null
}
```

#### `DELETE /ibkr/orders/{order_id}`
Cancel an existing order.

#### `GET /ibkr/orders/open`
Get all open orders.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/orders/open"
```

**Response:**
```json
[
  {
    "order_id": 1,
    "symbol": "AAPL",
    "sec_type": "STK",
    "action": "BUY",
    "quantity": 100.0,
    "order_type": "LMT",
    "status": "Submitted",
    "limit_price": 150.00,
    "aux_price": null,
    "filled": 0.0,
    "remaining": 100.0,
    "avg_fill_price": null
  }
]
```

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

#### `GET /ibkr/market_data/historical`
Get historical market data.

**Query Parameters:**
- `contract_id`: (Optional) Exactly one IBKR contract ID. Recommended for better performance - avoids symbol lookup
- `symbol`: (Optional) The ticker symbol. Required if `contract_id` not provided
- `sec_type`: Security type (e.g., "STK", "OPT", "FUT") - used with symbol
- `exchange`: Exchange (e.g., "SMART", "ISLAND") - used with symbol
- `currency`: Currency (e.g., "USD")
- `duration`: Data duration (e.g., "1 D", "1 W", "1 M", "1 Y")
- `bar_size`: Bar size (e.g., "1 min", "5 mins", "1 hour", "1 day")
- `what_to_show`: Data type (e.g., "TRADES", "MIDPOINT", "BID", "ASK")
- `use_rth`: Use regular trading hours only (true/false)
- `end_date`: (Optional) End date for historical data. Formats:
  - Date only: `YYYYMMDD` (e.g., `20260223`) - converted to `YYYYMMDD 15:59:00 {timezone}`
  - Date with time: `YYYYMMDD HH:MM:SS` (e.g., `20260223 15:30:00`)
  - Full: `YYYYMMDD HH:MM:SS Timezone` (e.g., `20260223 15:30:00 US/Eastern`)

**Note:** Either `symbol` or `contract_id` must be provided. Using `contract_id` is recommended as it avoids symbol lookup and is more efficient.

**Example with contract_id (recommended):**
```bash
curl -X GET "http://localhost:8000/ibkr/market_data/historical?contract_id=265598&duration=1%20D&bar_size=1%20min&what_to_show=TRADES&use_rth=true"
```

**Example with end_date:**
```bash
# Date only - will be converted to end of trading day with timezone
curl -X GET "http://localhost:8000/ibkr/market_data/historical?contract_id=265598&duration=5%20D&bar_size=1%20day&end_date=20260220"

# Date with time - used as-is
curl -X GET "http://localhost:8000/ibkr/market_data/historical?contract_id=265598&duration=5%20D&bar_size=1%20day&end_date=20260220%2015:30:00"
```

**Response:**
```json
[
  {
    "date": "2025-10-05T09:30:00",
    "open": 155.25,
    "high": 155.40,
    "low": 155.10,
    "close": 155.30,
    "volume": 2500,
    "wap": 155.25,
    "count": 125
  },
  {
    "date": "2025-10-05T09:35:00",
    "open": 155.30,
    "high": 155.75,
    "low": 155.25,
    "close": 155.70,
    "volume": 3200,
    "wap": 155.50,
    "count": 150
  }
]
```

#### `GET /ibkr/market_data`
Get real-time market data for a symbol or contract IDs.

**Query Parameters:**
- `symbol`: Symbol to get data for (e.g., AAPL)
- `contract_ids`: (Optional) One or more IBKR contract IDs. Pass multiple times for multiple contracts, e.g., `?contract_ids=265598&contract_ids=123456`
- `sec_type`: Security type (e.g., STK, OPT, FUT) - used with symbol (default: STK)
- `exchange`: Exchange (e.g., SMART, ISLAND) - used with symbol (default: SMART)
- `currency`: Currency (e.g., USD) - used with symbol (default: USD)
- `subscription_type`: Type of market data subscription (realtime or delayed, default: realtime)

**Note:** Either `symbol` or `contract_ids` must be provided. Using `symbol` is recommended for better performance.

**Example with symbol:**
```bash
curl -X GET "http://localhost:8000/ibkr/market_data?symbol=AAPL&subscription_type=delayed" -H "Accept: application/json"
```

**Example with contract_ids:**
```bash
curl -X GET "http://localhost:8000/ibkr/market_data?contract_ids=265598&contract_ids=123456"
```

**Response:**
```json
[
  {
    "contract_id": 265598,
    "symbol": "AAPL",
    "sec_type": "STK",
    "last": 263.55,
    "close": 272.95,
    "bid": null,
    "ask": null,
    "bid_size": null,
    "ask_size": null,
    "high": 272.81,
    "low": 262.89,
     "volume": 724566,
     "mark": null,
     "high_52_week": null,
     "low_52_week": null,
     "open_interest": null,
     "greeks": null,
     "timestamp": "2026-02-28T12:08:47.821499+00:00",
     "last_trade_time": "2026-02-28T12:07:55+00:00",
     "market_data_type": 3
  }
]
```

### Fundamental Data

#### `GET /ibkr/fundamental`
Get fundamental data for a contract, including earnings dates, dividend information, and financial metrics.

**Query Parameters:**
- `contract_id`: (Optional) IBKR contract ID. If provided, symbol lookup is skipped.
- `symbol`: (Optional) Symbol to look up (e.g., AAPL). Required if `contract_id` not provided.
- `sec_type`: Security type (e.g., STK, OPT, FUT) - used with symbol (default: STK)
- `exchange`: Exchange (e.g., SMART, ISLAND) - used with symbol
- `currency`: Currency (e.g., USD) - used with symbol
- `report_type`: Fundamental report type (default: CalendarReport)
  - `CalendarReport`: Earnings dates, dividend calendar
  - `ReportsFinSummary`: Financial summary (P/E, revenue, etc.)
  - `ReportSnapshot`: Company snapshot (ratios, dividend yield)
  - `ReportsFinStatements`: Full financial statements
  - `RESC`: Analyst estimates
  - `ReportsOwnership`: Company ownership

**Note:** Either `symbol` or `contract_id` must be provided. Using `contract_id` is recommended.

**Example - CalendarReport (earnings & dividends):**
```bash
curl -X GET "http://localhost:8000/ibkr/fundamental?symbol=AAPL&report_type=CalendarReport"
```

**Response:**
```json
{
  "contract_id": 265598,
  "symbol": "AAPL",
  "sec_type": "STK",
  "report_type": "CalendarReport",
  "next_earnings_date": "2025-01-15",
  "earnings_estimate": 1.45,
  "earnings_actual": 1.50,
  "earnings_history": [
    {"period": "2024-10-15", "estimate": 1.30, "actual": 1.35}
  ],
  "dividend_yield": null,
  "next_dividend": {
    "ex_date": "2025-01-10",
    "pay_date": "2025-01-20",
    "amount": 0.24
  },
  "dividend_history": [
    {"ex_date": "2024-10-10", "pay_date": "2024-10-20", "amount": 0.24}
  ],
  "pe_ratio": null,
  "raw_xml": "..."
}
```

**Example - ReportSnapshot (financial metrics):**
```bash
curl -X GET "http://localhost:8000/ibkr/fundamental?contract_id=265598&report_type=ReportSnapshot"
```

**Response:**
```json
{
  "contract_id": 265598,
  "symbol": "AAPL",
  "sec_type": "STK",
  "report_type": "ReportSnapshot",
  "next_earnings_date": null,
  "pe_ratio": 28.5,
  "dividend_yield": 0.006,
  "market_cap": 1750000000000.0,
  "sector": "Technology",
  "full_name": "Apple Inc.",
  "raw_xml": "..."
}
```

### Contract Management

#### `GET /ibkr/contract_details`
Get detailed information about a contract.

**Query Parameters:**
- `symbol`: The symbol (e.g., AAPL)
- `sec_type`: Security type (e.g., STK, OPT, FUT)
- `exchange`: Exchange (e.g., SMART, ISLAND)
- `primary_exchange`: Primary exchange (e.g., NASDAQ, NYSE)
- `currency`: Currency (e.g., USD)
- `options`: Optional parameters as JSON string including:
  - `last_trade_date_or_contract_month`: Expiry date for options - "YYYYMMDD"
  - `strike`: Strike price (for options)
  - `right`: Right for options - "C" or "P"
  - `trading_class`: Trading class (e.g., SPXW for weekly SPX options)

**Returns:**
- `qualified_contract`: A single contract dict when a unique match is found
- `candidate_contracts`: A list of contract candidates when multiple matches exist
- `error`: Error message when the request fails

**Example - Qualified Contract (single match):**
When the query is specific enough (e.g., includes currency), a single qualified contract is returned:
```bash
curl -X GET "http://localhost:8000/ibkr/contract_details?symbol=CCJ&sec_type=STK&exchange=SMART&currency=USD"
```

**Response:**
```json
{
  "qualified_contract": {
    "sec_type": "STK",
    "con_id": 1447060,
    "symbol": "CCJ",
    "last_trade_date_or_contract_month": "",
    "strike": 0.0,
    "right": "",
    "multiplier": "",
    "exchange": "SMART",
    "primary_exchange": "NYSE",
    "currency": "USD",
    "local_symbol": "CCJ",
    "trading_class": "CCJ",
    "include_expired": false,
    "sec_id_type": "",
    "sec_id": "",
    "description": "",
    "issuer_id": "",
    "combo_legs_descrip": "",
    "combo_legs": [],
    "delta_neutral_contract": null
  }
}
```

**Example - Candidate Contracts (ambiguous match):**
When the query is ambiguous (e.g., missing currency), multiple contract candidates are returned:
```bash
curl -X GET "http://localhost:8000/ibkr/contract_details?symbol=CCJ&sec_type=STK&exchange=SMART"
```

**Response:**
```json
{
  "candidate_contracts": [
    {
      "sec_type": "STK",
      "con_id": 1447060,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "",
      "strike": 0.0,
      "right": "",
      "multiplier": "",
      "exchange": "SMART",
      "primary_exchange": "NYSE",
      "currency": "USD",
      "local_symbol": "CCJ",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "STK",
      "con_id": 81540716,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "",
      "strike": 0.0,
      "right": "",
      "multiplier": "",
      "exchange": "SMART",
      "primary_exchange": "FWB2",
      "currency": "EUR",
      "local_symbol": "CCJ",
      "trading_class": "XETRA",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    }
  ]
}
```

#### `GET /ibkr/options_chain`
Get options chain for a given underlying contract.

**Query Parameters:**
- `underlying_symbol`: Symbol of the underlying contract (e.g., CCJ)
- `underlying_sec_type`: Security type of the underlying contract (e.g., STK)
- `underlying_con_id`: ConID of the underlying contract (e.g., 1447060)
- `exchange`: Exchange to filter chains by (e.g., SMART, CBOE). If not specified and multiple chains are available, returns a list of candidate chains.
- `filters`: Dictionary of filters to apply to the options chain (optional). You must specify at least one filter (including expirations) to reduce the number of options in the chain.
  - `trading_class`: List of trading classes to filter by (e.g., ["CCJ"])
  - `expirations`: List of expirations to filter by (e.g., ["20270206"])
  - `strikes`: List of strikes to filter by (e.g., [120])
  - `rights`: List of rights to filter by (e.g., ["C"] for calls, ["P"] for puts)

**Returns:**
- `options_chain`: List of option contracts when a single chain is found and filters are provided
- `candidate_chains`: List of candidate chains when multiple matches exist or no filters are provided
- `error`: Error message when the request fails

**Example 1 - Multiple Candidate Chains (no exchange specified):**
When no exchange is specified and multiple option chains exist for different exchanges:
```bash
curl "http://localhost:8000/ibkr/options_chain?underlying_symbol=CCJ&underlying_sec_type=STK&underlying_con_id=1447060"
```

**Response:**
```json
{
  "candidate_chains": [
    {
      "exchange": "BOX",
      "underlying_con_id": "1447060",
      "trading_class": "CCJ",
      "expirations": ["20260206", "20260213", "20260220", "20260227", "20260306", "20260313", "20260320", "20260618", "20260918", "20261218", "20270115", "20280121"],
      "strikes": [20.0, 23.0, 25.0, 28.0, 30.0, 33.0, 35.0, 38.0, 40.0, 42.0, 45.0, 47.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 79.0, 80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0, 90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 120.0, 121.0, 122.0, 123.0, 124.0, 125.0, 126.0, 127.0, 128.0, 129.0, 130.0, 131.0, 132.0, 133.0, 134.0, 135.0, 136.0, 137.0, 138.0, 139.0, 140.0, 141.0, 142.0, 143.0, 144.0, 145.0, 146.0, 147.0, 148.0, 149.0, 150.0, 152.5, 155.0, 157.5, 160.0, 162.5, 165.0, 170.0, 175.0, 180.0, 185.0, 190.0, 195.0]
    },
    {
      "exchange": "NASDAQOM",
      "underlying_con_id": "1447060",
      "trading_class": "CCJ",
      "expirations": ["20260206", "20260213", "20260220", "20260227", "20260306", "20260313", "20260320", "20260618", "20260918", "20261218", "20270115", "20280121"],
      "strikes": [20.0, 23.0, 25.0, 28.0, 30.0, 33.0, 35.0, 38.0, 40.0, 42.0, 45.0, 47.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 79.0, 80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0, 90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 120.0, 121.0, 122.0, 123.0, 124.0, 125.0, 126.0, 127.0, 128.0, 129.0, 130.0, 131.0, 132.0, 133.0, 134.0, 135.0, 136.0, 137.0, 138.0, 139.0, 140.0, 141.0, 142.0, 143.0, 144.0, 145.0, 146.0, 147.0, 148.0, 149.0, 150.0, 152.5, 155.0, 157.5, 160.0, 162.5, 165.0, 170.0, 175.0, 180.0, 185.0, 190.0, 195.0]
    }
  ]
}
```

**Example 2 - Single Candidate Chain (exchange specified, but no filters):**
When an exchange is specified but no filters are provided (filters are required to return specific option contracts):
```bash
curl "http://localhost:8000/ibkr/options_chain?underlying_symbol=CCJ&underlying_sec_type=STK&underlying_con_id=1447060&exchange=SMART"
```

**Response:**
```json
{
  "candidate_chains": [
    {
      "exchange": "SMART",
      "underlying_con_id": "1447060",
      "trading_class": "CCJ",
      "expirations": ["20260206", "20260213", "20260220", "20260227", "20260306", "20260313", "20260320", "20260618", "20260918", "20261218", "20270115", "20280121"],
      "strikes": [20.0, 23.0, 25.0, 28.0, 30.0, 33.0, 35.0, 38.0, 40.0, 42.0, 45.0, 47.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 79.0, 80.0, 81.0, 82.0, 83.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0, 90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 120.0, 121.0, 122.0, 123.0, 124.0, 125.0, 126.0, 127.0, 128.0, 129.0, 130.0, 131.0, 132.0, 133.0, 134.0, 135.0, 136.0, 137.0, 138.0, 139.0, 140.0, 141.0, 142.0, 143.0, 144.0, 145.0, 146.0, 147.0, 148.0, 149.0, 150.0, 152.5, 155.0, 157.5, 160.0, 162.5, 165.0, 170.0, 175.0, 180.0, 185.0, 190.0, 195.0]
    }
  ]
}
```

**Example 3 - Options Chain (exchange and filters provided):**
When both an exchange is specified and filters are provided, specific option contracts are returned:
```bash
curl "http://localhost:8000/ibkr/options_chain?underlying_symbol=CCJ&underlying_sec_type=STK&underlying_con_id=1447060&exchange=SMART&filters=%7B%22trading_class%22%3A%5B%22CCJ%22%5D%2C%22expirations%22%3A%5B%2220270115%22%2C%2220280121%22%5D%2C%22strikes%22%3A%5B120%2C130%5D%2C%22rights%22%3A%5B%22C%22%2C%22P%22%5D%7D"
```

**Response:**
```json
{
  "options_chain": [
    {
      "sec_type": "OPT",
      "con_id": 814588219,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20270115",
      "strike": 120.0,
      "right": "C",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   270115C00120000",
      "friendly_symbol": "CCJ Jan15'27 120.0 CALL",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 814233597,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20280121",
      "strike": 120.0,
      "right": "C",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   280121C00120000",
      "friendly_symbol": "CCJ Jan21'28 120.0 CALL",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 817259062,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20270115",
      "strike": 130.0,
      "right": "C",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   270115C00130000",
      "friendly_symbol": "CCJ Jan15'27 130.0 CALL",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 817259178,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20280121",
      "strike": 130.0,
      "right": "C",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   280121C00130000",
      "friendly_symbol": "CCJ Jan21'28 130.0 CALL",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 814588293,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20270115",
      "strike": 120.0,
      "right": "P",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   270115P00120000",
      "friendly_symbol": "CCJ Jan15'27 120.0 PUT",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 814234636,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20280121",
      "strike": 120.0,
      "right": "P",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   280121P00120000",
      "friendly_symbol": "CCJ Jan21'28 120.0 PUT",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 817259128,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20270115",
      "strike": 130.0,
      "right": "P",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   270115P00130000",
      "friendly_symbol": "CCJ Jan15'27 130.0 PUT",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    },
    {
      "sec_type": "OPT",
      "con_id": 817259236,
      "symbol": "CCJ",
      "last_trade_date_or_contract_month": "20280121",
      "strike": 130.0,
      "right": "P",
      "multiplier": "100",
      "exchange": "SMART",
      "primary_exchange": "",
      "currency": "USD",
      "local_symbol": "CCJ   280121P00130000",
      "friendly_symbol": "CCJ Jan21'28 130.0 PUT",
      "trading_class": "CCJ",
      "include_expired": false,
      "sec_id_type": "",
      "sec_id": "",
      "description": "",
      "issuer_id": "",
      "combo_legs_descrip": "",
      "combo_legs": [],
      "delta_neutral_contract": null
    }
  ]
}
```

### Scanner Operations

#### `GET /ibkr/scanner/workflow`
Get step-by-step workflow for using scanner effectively.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/workflow"
```

#### `GET /ibkr/scanner/instrument_codes`
Get available scanner instrument codes with descriptions.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/instrument_codes"
```

#### `GET /ibkr/scanner/location_codes`
Get available scanner location codes with descriptions.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/location_codes"
```

#### `GET /ibkr/scanner/scan_codes`
Get available scanner scan codes with descriptions.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/scan_codes"
```

#### `GET /ibkr/scanner/filter_codes`
Get available scanner filter codes with examples and usage hints.

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/filter_codes"
```

#### `GET /ibkr/scanner/results`
Run a market scanner with specified parameters.

**Query Parameters:**
- `instrument_code`: Instrument type (e.g., "STK", "FUT", "OPT"). Call `get_scanner_instrument_codes()` first.
- `location_code`: Location code (e.g., "STK.US", "STK.EU"). Call `get_scanner_location_codes()` first.
- `scan_code`: Scan code for predefined scans (e.g., "TOP_PERC_GAIN", "MOST_ACTIVE"). Call `get_scanner_scan_codes()` first. Must submit `scan_code`; "MOST_ACTIVE" is a good default.
- `filters`: Comma-separated filters in `parameter=value` format to fine-tune `scan_code` results. Call `get_scanner_filter_codes()` first.
  - Examples: `priceAbove=10,marketCapAbove1e6=1000` or `priceAbove=10,avgVolumeAbove=1000000`
- `max_results`: Maximum number of results to return (1-50, default: 50)

**Example:**
```bash
curl -X GET "http://localhost:8000/ibkr/scanner/results?instrument_code=STK&location_code=STK.US&scan_code=TOP_PERC_GAIN&max_results=25"
```

**Response:**
```json
"I found 3 stocks matching the scanner parameters: ['AAPL', 'MSFT', 'GOOGL']"
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
  "host": "localhost",
  "port": 8888,
  "client_id": 0,
  "accounts": ["DU123456"]
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
- **Container fails to start / "Permission denied" on the password file**: the file at `IB_GATEWAY_PASSWORD_FILE` must be readable by uid `911` (the container's `abc` user). Use `sudo chown root:911 <file> && sudo chmod 0440 <file>` (recommended) or `chmod 0604 <file>` for a less strict alternative. See the [Credentials Setup](#credentials-setup) section.
- **API socket never opens (TWS logs show login complete but no `4002` listener)**: confirm with `docker exec ibkr-gateway cat /proc/net/tcp /proc/net/tcp6 | awk '/0A/ {print}'` — TWS often binds only to IPv6 (`[::]:4002`), which is fine because the MCP client connects via `127.0.0.1` and Linux dual-stack routing accepts it. If only an IPv4 listener is missing, the container's socat is unable to forward and `/ibkr/connection/status` will stay `false` until TWS opens the socket.

## Debugging

### Viewing Application Logs

The application logs to both console and file (when enabled). To enable file logging, add to your `.env` file:

```bash
ENABLE_FILE_LOGGING=true
LOG_FILE_PATH=logs/app.log
LOG_LEVEL=INFO
```

View logs in real-time:

```bash
# Watch the log file
tail -f logs/app.log

# Or use the log file path directly
cat logs/app.log
```

### Using curl to Test Endpoints

Start the server:

```bash
./run.sh
```

Then test with curl commands:

```bash
# Check server is running
curl http://localhost:8000/

# Check IBKR Gateway status
curl http://localhost:8000/gateway/status

# Get Gateway container logs
curl http://localhost:8000/gateway/logs?tail=50

# Check connection status
curl http://localhost:8000/ibkr/connection/status

# Get account summary
curl http://localhost:8000/ibkr/account/summary

# Get positions
curl http://localhost:8000/ibkr/account/positions

# Get market data (example with AAPL)
curl "http://localhost:8000/ibkr/market_data?symbol=AAPL"
```

### API Documentation

Full API documentation is available at: http://localhost:8000/docs

MCP server is available at: http://localhost:8000/mcp

## TODO / Future Work

- Have a look at this to: https://github.com/jgalea/ibkr-mcp

## License

MIT License

## Appendix 1: Generic Ticks Reference

The server requests generic ticks alongside real-time market data to enrich the `MarketData` response. The following generic ticks are used (set in `app/services/market_data.py`):

| Tick | Name | Description |
|------|------|-------------|
| 100 | Option Volume | Option volume (put/call) |
| 101 | Option Open Interest | Option open interest (put/call) |
| 104 | Historical Volatility | Historical volatility |
| 106 | Implied Volatility | Option implied volatility |
| 165 | 52-Week High/Low | 52-week high and low prices |
| 221 | Mark Price | Generic mark price |

These map to the `MarketData` response fields as follows:

| Generic Tick | MarketData Field | ib_async Ticker Attribute |
|--------------|------------------|--------------------------|
| 100 | (requested, not mapped by ib_async) | — |
| 101 | (requested, not mapped by ib_async) | — |
| 104 | _valid_value(row["histVolatility"]) | `histVolatility` |
| 106 | _valid_value(row["impliedVolatility"]) | `impliedVolatility` |
| 165 | `high_52_week`, `low_52_week` | `high52`, `low52` |
| 221 | `mark` | `mark` |

**Additional fields not from generic ticks:**

| MarketData Field | ib_async Ticker Attribute | Tick Type |
|------------------|--------------------------|-----------|
| `timestamp` | `time` | 2 (TIME) |
| `last_trade_time` | `lastTimestamp` / `delayedLastTimestamp` | 45 / 88 |
| `volume` | `volume` | 8 (VOLUME) |
| `open_interest` | `openInterest` | 22 (OPEN_INTEREST) |

**Note:** Generic ticks 100 and 101 are requested but not mapped in ib_async's `GENERIC_TICK_MAP`. The `volume` field uses `ticker.volume` (tick type 8) and `open_interest` uses `ticker.openInterest` (tick type 22). For options, these are the per-contract volume and open interest.
